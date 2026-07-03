"""
interface/cli.py - Command-line interface for JARVIS-Lite.
Handles push-to-talk (SPACE key via pynput) and text input mode.

Source of truth: Implementation_plan.md §5.2
"""

import sys
import time
import threading
from typing import Optional

from interface.ui import TerminalUI
from core.hotkeys import HotkeyManager
from models import State
from utils.logger import JarvisLogger


logger = JarvisLogger()


class CLI:
    """Command-line interface for JARVIS-Lite."""

    def __init__(self, jarvis_engine):
        self.engine = jarvis_engine
        self.ui = TerminalUI()
        self.hotkeys = HotkeyManager()
        self.running = True
        self.no_voice = False

        # Push-to-talk state
        self._ptt_active = False
        self._ptt_lock = threading.Lock()

    def run(self):
        """Main event loop."""
        # Show startup and initialize
        self.ui.show_startup()
        self.engine.initialize(progress_callback=self.ui.show_loading_step)
        self.ui.show_startup_complete()

        # Configure silence detection from audio config
        audio_cfg = self.engine.config_manager.config.get('audio', {})
        self.engine.audio.configure_silence_detection(
            threshold=audio_cfg.get('silence_threshold', 0.01),
            duration_ms=audio_cfg.get('silence_duration_ms', 800),
            max_seconds=audio_cfg.get('max_recording_seconds', 10)
        )

        # Initialize hotkey manager
        hotkeys_config = self.engine.config_manager.config.get('hotkeys', {})
        self.hotkeys.initialize(config=hotkeys_config)

        if self.hotkeys.backend == "pynput":
            self.hotkeys.start(
                on_ptt_start=self._on_ptt_start,
                on_ptt_end=self._on_ptt_end,
                on_escape=self._on_escape,
                on_help=self._on_help_key,
            )

        # Main loop
        while self.running:
            self.ui.show_idle_prompt()

            text_input = self._wait_for_input()

            if text_input is None:
                continue  # PTT handled by hotkey callbacks
            elif text_input.lower() in ('exit', 'quit', 'bye', 'goodbye'):
                self._shutdown()
            elif text_input.lower() == 'help':
                self.ui.show_help()
                try:
                    input()  # Wait for Enter
                except (EOFError, KeyboardInterrupt):
                    pass
            elif text_input.strip():
                self._handle_text_input(text_input)

    def _wait_for_input(self) -> Optional[str]:
        """
        Wait for text input via stdin.
        Returns text if typed, None if nothing entered.
        """
        try:
            text = input()
            return text if text else None
        except EOFError:
            return 'exit'
        except KeyboardInterrupt:
            return 'exit'

    def _handle_text_input(self, text: str):
        """Process a typed text command."""
        self.ui.show_user_input(text)
        self.ui.show_processing("Understanding command")

        try:
            response = self.engine.process_text(text)
            self.ui.stop_all_animations()

            if response:
                self.ui.show_response(response)
            else:
                # HELP returns None — already handled
                pass
        except Exception as e:
            self.ui.stop_all_animations()
            self.ui.show_error("Processing Error", str(e),
                               "Try rephrasing your command.")
            logger.error(f"Error processing text: {e}", component="cli")

    # ========================================================================
    # PUSH-TO-TALK CALLBACKS
    # ========================================================================

    def _on_ptt_start(self):
        """Called when SPACE is pressed — start recording."""
        with self._ptt_lock:
            if self._ptt_active:
                return
            self._ptt_active = True

        self.ui.stop_all_animations()
        self.ui.show_listening()

        try:
            self.engine.audio.start_recording()
        except Exception as e:
            logger.error(f"Failed to start recording: {e}", component="cli")
            with self._ptt_lock:
                self._ptt_active = False

    def _on_ptt_end(self):
        """Called when SPACE is released — stop recording and process."""
        with self._ptt_lock:
            if not self._ptt_active:
                return
            self._ptt_active = False

        # Process in background thread to avoid blocking hotkey listener
        threading.Thread(target=self._process_voice, daemon=True).start()

    def _process_voice(self):
        """
        Process recorded voice input.

        Flow:
        1. Stop recording → AudioData
        2. Transcribe → text
        3. Show STT cancel window (1.5s)
        4. Parse + execute → response
        """
        try:
            audio_data = self.engine.audio.stop_recording()
            self.ui.stop_all_animations()

            if audio_data.duration < 0.3:
                self.ui.show_warning("Recording too short. Hold SPACE and speak.")
                return

            # Transcribe
            self.ui.show_processing("Processing speech")
            text = self.engine.process_audio(audio_data)
            self.ui.stop_all_animations()

            if text is None:
                self.ui.show_warning("Couldn't understand the audio. Try again.")
                return

            # Show what was heard with cancel window
            self.ui.show_stt_cancel_window(text)
            time.sleep(1.5)  # STT cancel window
            print()  # New line after cancel window

            # Process the text
            self.ui.show_user_input(text)
            self.ui.show_processing("Understanding command")
            response = self.engine.process_text(text)
            self.ui.stop_all_animations()

            if response:
                self.ui.show_response(response)

        except Exception as e:
            self.ui.stop_all_animations()
            self.ui.show_error("Voice Input Error", str(e),
                               "Check your microphone settings.")
            logger.error(f"Voice input error: {e}", component="cli")

    def _on_escape(self):
        """Called when ESC is pressed — cancel or barge-in."""
        # If TTS is speaking, interrupt it (barge-in)
        if self.engine.tts.is_speaking:
            self.engine.tts.stop()
            self.ui.stop_all_animations()
            self.ui.show_info("Speech interrupted.")
            return

        # If recording, cancel it
        with self._ptt_lock:
            if self._ptt_active:
                self._ptt_active = False
                self.engine.audio.stop_recording()
                self.ui.stop_all_animations()
                self.ui.show_info("Recording cancelled.")
                return

    def _on_help_key(self):
        """Called when F1 is pressed — show help."""
        self.ui.show_help()

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    def _shutdown(self):
        """Graceful shutdown sequence."""
        self.running = False
        self.hotkeys.stop()
        self.ui.stop_all_animations()
        print()
        self.ui.show_info("Shutting down JARVIS-Lite...")
        self.engine.shutdown()
        self.ui.show_complete("Goodbye!")
        print()
