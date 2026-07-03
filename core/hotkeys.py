"""
core/hotkeys.py - Global hotkey manager for JARVIS-Lite.
Handles push-to-talk (SPACE) and other keyboard shortcuts.

Uses: pynput (cross-platform keyboard listener)
Fallback: msvcrt on Windows if pynput unavailable

Source of truth: Implementation_plan.md §5.3
"""

import threading
from typing import Callable, Optional

from utils.logger import JarvisLogger


logger = JarvisLogger()


class HotkeyManager:
    """
    Global hotkey manager for push-to-talk and control shortcuts.

    Primary: pynput (cross-platform, works in background)
    Fallback: Simple input() polling (text-only mode)
    """

    def __init__(self):
        self._listener = None
        self._callbacks: dict = {}
        self._active = False
        self._ptt_held = False
        self._backend = "none"

    def initialize(self, config: dict = None) -> bool:
        """
        Initialize keyboard listener.

        Args:
            config: Hotkey configuration from settings.json['hotkeys']
        """
        config = config or {}

        try:
            from pynput import keyboard

            self._backend = "pynput"
            logger.info("Hotkey manager initialized (pynput)", component="hotkeys")
            return True

        except ImportError:
            logger.warning(
                "pynput not installed — push-to-talk disabled. "
                "Install with: pip install pynput",
                component="hotkeys"
            )
            self._backend = "fallback"
            return True  # Text mode still works

    def start(self, on_ptt_start: Callable = None,
              on_ptt_end: Callable = None,
              on_escape: Callable = None,
              on_help: Callable = None):
        """
        Start listening for hotkeys in background thread.

        Args:
            on_ptt_start: Called when SPACE is pressed (start recording)
            on_ptt_end: Called when SPACE is released (stop recording)
            on_escape: Called when ESC is pressed (cancel/barge-in)
            on_help: Called when F1 is pressed (show help)
        """
        if self._backend != "pynput":
            return

        self._callbacks = {
            'ptt_start': on_ptt_start,
            'ptt_end': on_ptt_end,
            'escape': on_escape,
            'help': on_help,
        }

        try:
            from pynput import keyboard

            def on_press(key):
                try:
                    if key == keyboard.Key.space:
                        if not self._ptt_held:
                            self._ptt_held = True
                            if self._callbacks.get('ptt_start'):
                                self._callbacks['ptt_start']()

                    elif key == keyboard.Key.esc:
                        if self._callbacks.get('escape'):
                            self._callbacks['escape']()

                    elif key == keyboard.Key.f1:
                        if self._callbacks.get('help'):
                            self._callbacks['help']()

                except Exception as e:
                    logger.error(f"Hotkey handler error: {e}",
                                 component="hotkeys")

            def on_release(key):
                try:
                    if key == keyboard.Key.space:
                        self._ptt_held = False
                        if self._callbacks.get('ptt_end'):
                            self._callbacks['ptt_end']()
                except Exception as e:
                    logger.error(f"Hotkey release error: {e}",
                                 component="hotkeys")

            self._listener = keyboard.Listener(
                on_press=on_press,
                on_release=on_release,
                suppress=False  # Don't suppress other apps' key events
            )
            self._listener.daemon = True
            self._listener.start()
            self._active = True

            logger.info("Hotkey listener started (SPACE=PTT, ESC=cancel, F1=help)",
                        component="hotkeys")

        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}",
                         component="hotkeys")

    def stop(self):
        """Stop the hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._active = False
        logger.debug("Hotkey listener stopped", component="hotkeys")

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def backend(self) -> str:
        return self._backend
