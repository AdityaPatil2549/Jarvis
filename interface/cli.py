"""
interface/cli.py - Command-line interface for JARVIS-Lite.
Handles push-to-talk (SPACE key) and text input mode.

Source of truth: Implementation_plan.md §5.2
"""

import sys
import time
import threading
from typing import Optional

from interface.ui import TerminalUI
from models import State
from utils.logger import JarvisLogger


logger = JarvisLogger()


class CLI:
    """Command-line interface for JARVIS-Lite."""

    def __init__(self, jarvis_engine):
        self.engine = jarvis_engine
        self.ui = TerminalUI()
        self.running = True
        self.ptt_key = 'space'

    def run(self):
        """Main event loop."""
        # Show startup and initialize
        self.ui.show_startup()
        self.engine.initialize(progress_callback=self.ui.show_loading_step)
        self.ui.show_startup_complete()

        while self.running:
            self.ui.show_idle_prompt()

            # Wait for text input (push-to-talk handled separately)
            text_input = self._wait_for_input()

            if text_input is None:
                # Push-to-talk: record audio
                self._handle_voice_input()
            elif text_input.lower() in ('exit', 'quit', 'bye', 'goodbye'):
                self._shutdown()
            elif text_input.lower() == 'help':
                self.ui.show_help()
                input()  # Wait for Enter
            elif text_input.strip():
                # Text command: skip STT, go straight to NLP
                self._handle_text_input(text_input)

    def _wait_for_input(self) -> Optional[str]:
        """
        Wait for text input via stdin.
        Returns text if typed, None if push-to-talk was triggered.

        For Phase 1 MVP, uses simple input(). Phase 2 will add
        global keyboard hooks for SPACE-key push-to-talk.
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
                self.ui.show_warning("I didn't understand that. Say 'help' for examples.")
        except Exception as e:
            self.ui.stop_all_animations()
            self.ui.show_error("Processing Error", str(e),
                               "Try rephrasing your command.")
            logger.error(f"Error processing text: {e}", component="cli")

    def _handle_voice_input(self):
        """
        Handle push-to-talk voice input.

        Flow:
        1. Show listening animation
        2. Record audio
        3. Show STT cancel window
        4. Process through engine
        """
        self.ui.show_listening()

        try:
            # Record audio
            self.engine.audio.start_recording()

            # Wait for silence or timeout
            start_time = time.time()
            max_duration = 10  # seconds

            while time.time() - start_time < max_duration:
                if not self.engine.audio.is_recording():
                    break
                time.sleep(0.1)

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

    def _shutdown(self):
        """Graceful shutdown sequence."""
        self.running = False
        self.ui.stop_all_animations()
        print()
        self.ui.show_info("Shutting down JARVIS-Lite...")
        self.engine.shutdown()
        self.ui.show_complete("Goodbye!")
        print()
