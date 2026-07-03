"""
core/tts.py - Text-to-Speech for JARVIS-Lite.
Implements TTSInterface ABC + Pyttsx3TTS with barge-in support.

Source of truth: Backend_schema.md §3.4, Implementation_plan.md §3.7,
                 Architecture_Enhancements.md §1
"""

import threading
from abc import ABC, abstractmethod
from typing import Optional

from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class TTSInterface(ABC):
    """Abstract interface for text-to-speech engines."""

    @abstractmethod
    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        pass

    @abstractmethod
    def speak(self, text: str) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        """Immediately stop ongoing speech (barge-in)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        pass


# ============================================================================
# PYTTSX3 IMPLEMENTATION
# ============================================================================

class Pyttsx3TTS(TTSInterface):
    """
    pyttsx3 text-to-speech engine with barge-in (interrupt) support.

    Architecture:
    - TTS runs in a dedicated daemon thread to avoid blocking the main loop.
    - A threading.Event (tts_interrupt_flag) is checked during speech.
    - When set, speech halts within ~100ms and control returns to LISTENING.
    """

    def __init__(self):
        self.engine = None
        self._speaking = False
        self._lock = threading.Lock()
        self.tts_interrupt_flag = threading.Event()
        self._speech_thread: Optional[threading.Thread] = None
        self._initialized = False

    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        """Initialize pyttsx3 engine."""
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            self._select_voice()
            self._initialized = True
            logger.info(f"TTS initialized (rate={rate}, volume={volume})",
                        component="tts")
            return True

        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3",
                         component="tts")
            return False
        except Exception as e:
            logger.error(f"TTS initialization failed: {e}", component="tts")
            return False

    def _select_voice(self):
        """Select best available voice (prefer male/neutral)."""
        if not self.engine:
            return

        voices = self.engine.getProperty('voices')
        # Windows: prefer SAPI5 David (en-US)
        # macOS: prefer Alex or Daniel
        # Linux: espeak default
        preferred = ['david', 'alex', 'daniel', 'mark', 'zira']
        for voice in voices:
            name_lower = voice.name.lower()
            if any(pref in name_lower for pref in preferred):
                self.engine.setProperty('voice', voice.id)
                logger.debug(f"Selected voice: {voice.name}", component="tts")
                return

        # Fall back to first available
        if voices:
            self.engine.setProperty('voice', voices[0].id)
            logger.debug(f"Using default voice: {voices[0].name}", component="tts")

    def speak(self, text: str) -> None:
        """
        Speak text in a background daemon thread.
        Supports barge-in: set tts_interrupt_flag to halt speech.
        """
        if not self._initialized or not self.engine:
            logger.warning("TTS not initialized, skipping speech", component="tts")
            return

        # Clear any previous interrupt flag
        self.tts_interrupt_flag.clear()

        # Run speech in daemon thread to avoid blocking
        self._speech_thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True
        )
        self._speech_thread.start()

    def _speak_worker(self, text: str):
        """Worker thread for TTS. Checks interrupt flag between sentences."""
        try:
            with self._lock:
                self._speaking = True

            # Split text into sentences for granular interrupt checking
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)

            for sentence in sentences:
                # Check interrupt flag before each sentence
                if self.tts_interrupt_flag.is_set():
                    logger.debug("TTS interrupted (barge-in)", component="tts")
                    break

                sentence = sentence.strip()
                if not sentence:
                    continue

                self.engine.say(sentence)
                self.engine.runAndWait()

        except Exception as e:
            logger.error(f"TTS error: {e}", component="tts")
        finally:
            with self._lock:
                self._speaking = False

    def stop(self) -> None:
        """Immediately stop ongoing speech (barge-in)."""
        self.tts_interrupt_flag.set()
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        with self._lock:
            self._speaking = False
        logger.debug("TTS stopped (barge-in)", component="tts")

    @property
    def is_speaking(self) -> bool:
        """Return True if currently speaking."""
        with self._lock:
            return self._speaking

    def shutdown(self) -> None:
        """Clean up TTS resources."""
        self.stop()
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        self._initialized = False
        logger.debug("TTS shut down", component="tts")
