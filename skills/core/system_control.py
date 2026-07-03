"""
skills/core/system_control.py - System control skill.
Handles: VOLUME_CONTROL, SCREENSHOT, LOCK_SCREEN

Source of truth: Implementation_plan.md §4.5
"""

import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

from models import Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
from skills.base import BaseSkill
from utils.helpers import get_os
from utils.logger import JarvisLogger


logger = JarvisLogger()


class SystemControlSkill(BaseSkill):
    """Handles system-level operations: volume, screenshots, lock."""

    name = "system_control"
    version = "1.0.0"
    description = "Volume control, screenshots, and screen locking"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.screenshot_dir = Path.home() / "Desktop"

    def initialize(self) -> bool:
        screenshot_path = self.config.get('screenshot_dir', '~/Desktop')
        self.screenshot_dir = Path(screenshot_path).expanduser()
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        return True

    def get_handled_intents(self) -> List[IntentType]:
        return [IntentType.VOLUME_CONTROL, IntentType.SCREENSHOT,
                IntentType.LOCK_SCREEN]

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        handlers = {
            IntentType.VOLUME_CONTROL: self._adjust_volume,
            IntentType.SCREENSHOT:     self._take_screenshot,
            IntentType.LOCK_SCREEN:    self._lock_screen,
        }
        handler = handlers.get(intent.type)
        if handler:
            return handler(intent, context)
        return ExecutionResult(success=False, message="Unknown system operation")

    def _adjust_volume(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Adjust system volume up/down by 10%."""
        action = intent.parameters.get('action', 'up')
        os_name = get_os()

        try:
            if os_name == 'win':
                # Use nircmd or PowerShell for volume control
                if action == 'up':
                    subprocess.run(
                        ['powershell', '-Command',
                         '(New-Object -ComObject WScript.Shell).SendKeys([char]175)'],
                        capture_output=True, timeout=3
                    )
                elif action == 'down':
                    subprocess.run(
                        ['powershell', '-Command',
                         '(New-Object -ComObject WScript.Shell).SendKeys([char]174)'],
                        capture_output=True, timeout=3
                    )
                elif action == 'mute':
                    subprocess.run(
                        ['powershell', '-Command',
                         '(New-Object -ComObject WScript.Shell).SendKeys([char]173)'],
                        capture_output=True, timeout=3
                    )

            elif os_name == 'mac':
                if action == 'up':
                    subprocess.run(
                        ['osascript', '-e',
                         'set volume output volume ((output volume of (get volume settings)) + 10)'],
                        capture_output=True, timeout=3
                    )
                elif action == 'down':
                    subprocess.run(
                        ['osascript', '-e',
                         'set volume output volume ((output volume of (get volume settings)) - 10)'],
                        capture_output=True, timeout=3
                    )
                elif action == 'mute':
                    subprocess.run(
                        ['osascript', '-e', 'set volume with output muted'],
                        capture_output=True, timeout=3
                    )

            else:  # Linux
                if action == 'up':
                    subprocess.run(['amixer', 'set', 'Master', '10%+'],
                                   capture_output=True, timeout=3)
                elif action == 'down':
                    subprocess.run(['amixer', 'set', 'Master', '10%-'],
                                   capture_output=True, timeout=3)
                elif action == 'mute':
                    subprocess.run(['amixer', 'set', 'Master', 'toggle'],
                                   capture_output=True, timeout=3)

            msg = f"Volume {'muted' if action == 'mute' else action}"
            return ExecutionResult(success=True, message=msg)

        except Exception as e:
            return ExecutionResult(success=False,
                                  message=f"Volume control failed: {e}",
                                  error_type=ErrorType.EXECUTION_FAILED)

    def _take_screenshot(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Take a screenshot and save to desktop."""
        try:
            import pyautogui

            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            save_path = self.screenshot_dir / filename
            pyautogui.screenshot(str(save_path))

            return ExecutionResult(
                success=True,
                message=f"Screenshot saved: {filename}",
                data={'path': str(save_path)}
            )
        except ImportError:
            return ExecutionResult(
                success=False,
                message="pyautogui not installed. Run: pip install pyautogui",
                error_type=ErrorType.SYSTEM_ERROR
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Screenshot failed: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )

    def _lock_screen(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Lock the workstation."""
        os_name = get_os()

        try:
            if os_name == 'win':
                subprocess.run(['rundll32.exe', 'user32.dll,LockWorkStation'],
                               timeout=3)
            elif os_name == 'mac':
                subprocess.run(['pmset', 'displaysleepnow'], timeout=3)
            else:
                subprocess.run(['loginctl', 'lock-session'], timeout=3)

            return ExecutionResult(success=True, message="Screen locked")

        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Could not lock screen: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )
