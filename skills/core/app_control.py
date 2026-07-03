"""
skills/core/app_control.py - Application control skill.
Handles: OPEN_APP, CLOSE_APP

Source of truth: Implementation_plan.md §4.4
"""

import subprocess
import platform
from typing import List, Optional

from models import Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
from skills.base import BaseSkill
from utils.helpers import get_os
from utils.logger import JarvisLogger


logger = JarvisLogger()


# Default app map — overridden by config/settings.json
DEFAULT_APP_MAP = {
    'chrome':    {'win': 'chrome',    'mac': 'Google Chrome',       'linux': 'google-chrome'},
    'firefox':   {'win': 'firefox',   'mac': 'Firefox',             'linux': 'firefox'},
    'vscode':    {'win': 'code',      'mac': 'Visual Studio Code',  'linux': 'code'},
    'terminal':  {'win': 'cmd',       'mac': 'Terminal',            'linux': 'gnome-terminal'},
    'notepad':   {'win': 'notepad',   'mac': 'TextEdit',            'linux': 'gedit'},
    'explorer':  {'win': 'explorer',  'mac': 'Finder',              'linux': 'nautilus'},
}


class AppControlSkill(BaseSkill):
    """Handles opening and closing applications."""

    name = "app_control"
    version = "1.0.0"
    description = "Launch and close desktop applications"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.app_map = {}
        self._running_processes = {}

    def initialize(self) -> bool:
        self.app_map = self.config.get('app_map', DEFAULT_APP_MAP)
        logger.debug(f"AppControl initialized with {len(self.app_map)} apps",
                     component="skills")
        return True

    def get_handled_intents(self) -> List[IntentType]:
        return [IntentType.OPEN_APP, IntentType.CLOSE_APP]

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        if intent.type == IntentType.OPEN_APP:
            return self._open_app(intent, context)
        elif intent.type == IntentType.CLOSE_APP:
            return self._close_app(intent, context)
        return ExecutionResult(success=False, message="Unknown app operation")

    def _open_app(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Launch an application."""
        app_name = intent.parameters.get('app_name', '')
        if not app_name:
            return ExecutionResult(success=False, message="No application specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        # Look up in app map
        app_entry = self.app_map.get(app_name)
        if not app_entry:
            return ExecutionResult(
                success=False,
                message=f"Unknown application: '{app_name}'. "
                        f"Known apps: {', '.join(self.app_map.keys())}",
                error_type=ErrorType.INVALID_COMMAND
            )

        os_name = get_os()
        executable = app_entry.get(os_name, app_entry.get('win', app_name))

        try:
            if os_name == 'win':
                proc = subprocess.Popen(
                    f'start "" "{executable}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif os_name == 'mac':
                proc = subprocess.Popen(
                    ['open', '-a', executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                proc = subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            self._running_processes[app_name] = proc
            context.set_variable('last_opened_app', app_name)

            return ExecutionResult(
                success=True,
                message=f"Launching {app_name}"
            )

        except FileNotFoundError:
            return ExecutionResult(
                success=False,
                message=f"Application '{executable}' not found on this system.",
                error_type=ErrorType.FILE_NOT_FOUND
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Could not launch {app_name}: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )

    def _close_app(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Close a running application."""
        app_name = intent.parameters.get('app_name', '')
        if not app_name:
            return ExecutionResult(success=False, message="No application specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        os_name = get_os()
        app_entry = self.app_map.get(app_name, {})
        executable = app_entry.get(os_name, app_name) if app_entry else app_name

        try:
            if os_name == 'win':
                subprocess.run(
                    ['taskkill', '/IM', f'{executable}.exe', '/F'],
                    capture_output=True, timeout=3
                )
            elif os_name == 'mac':
                subprocess.run(
                    ['osascript', '-e', f'quit app "{executable}"'],
                    capture_output=True, timeout=3
                )
            else:
                subprocess.run(
                    ['pkill', '-f', executable],
                    capture_output=True, timeout=3
                )

            # Also kill tracked process
            proc = self._running_processes.pop(app_name, None)
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()

            return ExecutionResult(success=True, message=f"Closed {app_name}")

        except subprocess.TimeoutExpired:
            return ExecutionResult(success=False,
                                  message=f"Timeout closing {app_name}",
                                  error_type=ErrorType.COMMAND_TIMEOUT)
        except Exception as e:
            return ExecutionResult(success=False,
                                  message=f"Could not close {app_name}: {e}",
                                  error_type=ErrorType.EXECUTION_FAILED)
