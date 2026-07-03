"""
jarvis_engine.py - JARVIS Engine — Orchestrates all components.
Implements the state machine from Appflow.md §2.

Source of truth: Implementation_plan.md §6.1
"""

import time
from typing import Optional, Callable

from models import (
    State, IntentType, ConversationContext, SystemConfig,
    AudioData, ExecutionResult
)
from core.audio import SoundDeviceAudio
from core.stt import FasterWhisperSTT, VoskSTT
from core.nlp import RuleBasedNLP
from core.tts import KokoroTTS, Pyttsx3TTS
from core.executor import SkillBasedExecutor
from core.config_manager import ConfigManager
from core.model_manager import ModelManager
from core.context import save_context, load_context
from skills.manager import SkillManager
from utils.logger import JarvisLogger
from utils.security import is_dangerous_command


logger = JarvisLogger()


class JarvisEngine:
    """Main orchestrator for JARVIS-Lite."""

    def __init__(self):
        self.state = State.INITIALIZING
        self.context = ConversationContext()
        self.config_manager = ConfigManager()
        self.config: Optional[SystemConfig] = None

        # Components (initialized in initialize())
        self.audio = SoundDeviceAudio()
        self.stt = FasterWhisperSTT()
        self.stt_fallback = VoskSTT()
        self.nlp = RuleBasedNLP()
        self.tts = KokoroTTS()            # Primary: Kokoro neural TTS
        self.tts_fallback = Pyttsx3TTS()  # Fallback: system SAPI5/espeak
        self.skill_manager = SkillManager()
        self.executor: Optional[SkillBasedExecutor] = None
        self.model_manager = ModelManager(self.stt, self.nlp)

    def initialize(self, progress_callback: Optional[Callable] = None) -> bool:
        """
        Initialize all components following INITIALIZING state (Appflow §2.2).
        Calls progress_callback(message, duration) at each step.

        Returns True if all critical components loaded.
        """
        def progress(msg: str, duration: float = 0.5):
            if progress_callback:
                progress_callback(msg, duration)
            logger.info(msg, component="engine")

        try:
            # Step 1: Load configuration (10%)
            progress("Loading configuration", 0.3)
            self.config = self.config_manager.load_all()

            # Reinitialize logger with verbosity from config
            if self.config.verbose_logging:
                JarvisLogger.reset()
                JarvisLogger(verbose=True, log_file="logs/jarvis.log")

            # Step 2: Initialize NLP (30%)
            progress("Initializing NLP engine", 0.5)
            if not self.nlp.initialize():
                logger.error("NLP initialization failed", component="engine")
                return False

            # Step 3: Initialize audio devices (50%)
            progress("Initializing audio devices", 0.5)
            audio_initialized = self.audio.initialize(self.config.audio)
            if not audio_initialized:
                logger.warning("Audio not available — text-only mode",
                               component="engine")

            # Step 4: Load faster-whisper STT model (80%)
            progress("Loading speech recognition model (faster-whisper)", 1.5)
            stt_loaded = self.stt.initialize(model=self.config.stt_model)
            if not stt_loaded:
                logger.warning("faster-whisper not available, trying Vosk fallback",
                               component="engine")
                self.stt_fallback.initialize()

            # Step 5: Initialize TTS (90%) — Kokoro primary, pyttsx3 fallback
            progress("Initializing text-to-speech (Kokoro)", 0.5)
            # Pass voice and language config to Kokoro before init
            self.tts.voice = self.config.tts_voice
            self.tts.lang_code = self.config.tts_lang_code
            tts_loaded = self.tts.initialize(
                rate=self.config.tts_rate,
                volume=self.config.tts_volume
            )
            if not tts_loaded:
                logger.warning("Kokoro TTS unavailable, falling back to pyttsx3",
                               component="engine")
                self.tts = self.tts_fallback
                self.tts.initialize(
                    rate=self.config.tts_rate,
                    volume=self.config.tts_volume
                )

            # Step 6: Load skills (95%)
            progress("Loading skills", 0.5)
            skills_config = self.config_manager.config.get('skills', {})
            self.skill_manager.discover_and_load(config=skills_config)

            # Wire up executor and macro skill
            self.executor = SkillBasedExecutor(skill_manager=self.skill_manager)
            macro_skill = self.skill_manager.get_skill('macro_skill')
            if macro_skill:
                macro_skill.set_executor(self.executor)
                macro_skill.set_macros(self.config_manager.macros)

            # Step 7: Initialize VRAM manager
            self.model_manager.initialize()

            # Step 8: Load conversation context
            progress("Loading session context", 0.3)
            self.context = load_context()

            # Done
            progress("System ready", 0.2)
            self.state = State.IDLE
            logger.info("JARVIS-Lite initialized successfully",
                        component="engine")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", component="engine")
            self.state = State.ERROR
            return False

    def process_audio(self, audio_data: AudioData) -> Optional[str]:
        """TRANSCRIBING state: audio → text."""
        self.state = State.TRANSCRIBING
        self.model_manager.prepare_for_stt()

        text = self.stt.transcribe(audio_data)
        if text is None:
            # Try fallback
            text = self.stt_fallback.transcribe(audio_data)

        self.state = State.IDLE
        return text

    def process_text(self, text: str) -> Optional[str]:
        """PARSING + EXECUTING + RESPONDING: text → response."""

        # ── Security check ─────────────────────────────────────────────
        if is_dangerous_command(text):
            response = "I can't do that — it looks like a dangerous command."
            self.tts.speak(response)
            return response

        # ── Parse intent ───────────────────────────────────────────────
        self.state = State.PARSING
        self.model_manager.prepare_for_nlp()
        parse_result = self.nlp.parse_intent(text, self.context)

        # Handle HELP inline
        if parse_result.intent and parse_result.intent.type == IntentType.HELP:
            return None  # Handled by CLI

        # Handle EXIT inline
        if parse_result.intent and parse_result.intent.type == IntentType.EXIT:
            return "Goodbye!"

        # Handle clarification needed
        if parse_result.requires_clarification:
            self.state = State.CLARIFYING
            msg = parse_result.clarification_message or "Could you clarify?"

            if parse_result.below_confidence_floor:
                # "Did you mean X?" flow
                self.context.set_clarification(
                    parse_result.intent,
                    ['yes', 'no'],
                    msg
                )
            elif parse_result.clarification_options:
                self.context.set_clarification(
                    parse_result.intent,
                    parse_result.clarification_options,
                    msg
                )

            self.tts.speak(msg)
            self.state = State.IDLE
            return msg

        # Handle parse errors
        if parse_result.error or not parse_result.intent:
            self.state = State.IDLE
            response = "I didn't understand that. Say 'help' for examples."
            self.tts.speak(response)
            return response

        # ── Execute ────────────────────────────────────────────────────
        self.state = State.EXECUTING
        result = self.executor.execute(parse_result.intent, self.context)

        # ── Respond ────────────────────────────────────────────────────
        self.state = State.RESPONDING
        if result and result.success:
            response = result.message
        elif result:
            response = result.message
        else:
            response = "I don't know how to do that yet."

        # Update conversation context
        self.context.add_turn('user', text, intent=parse_result.intent)
        self.context.add_turn('assistant', response, result=result)

        # Speak response
        self.tts.speak(response)

        self.state = State.IDLE
        return response

    def shutdown(self):
        """Graceful shutdown of all components."""
        self.state = State.SHUTTING_DOWN
        logger.info("Shutting down JARVIS-Lite...", component="engine")

        # Save context
        if self.config and self.config.save_history:
            save_context(self.context)

        # Shutdown components
        self.tts.shutdown()
        self.stt.shutdown()
        self.stt_fallback.shutdown()
        self.nlp.shutdown()
        self.audio.shutdown()
        self.skill_manager.shutdown()
        self.model_manager.unload_all()

        logger.info("JARVIS-Lite shut down complete", component="engine")
