"""
skills/core/file_operations.py - File operations skill.
Handles: OPEN_FILE, SEARCH_FILES, CREATE_FILE, DELETE_FILE

Source of truth: Implementation_plan.md §4.3
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import List

from models import Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
from skills.base import BaseSkill
from utils.helpers import expand_path, get_os
from utils.logger import JarvisLogger


logger = JarvisLogger()


class FileOperationsSkill(BaseSkill):
    """Handles all file-related operations."""

    name = "file_operations"
    version = "1.0.0"
    description = "Open, search, create, and delete files"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.allowed_dirs: List[Path] = []

    def initialize(self) -> bool:
        raw_dirs = self.config.get('allowed_directories',
                                   ['~/Documents', '~/Desktop', '~/Downloads'])
        self.allowed_dirs = [expand_path(d) for d in raw_dirs]

        # Ensure directories exist
        for d in self.allowed_dirs:
            d.mkdir(parents=True, exist_ok=True)

        logger.debug(f"FileOperations initialized with {len(self.allowed_dirs)} dirs",
                     component="skills")
        return True

    def get_handled_intents(self) -> List[IntentType]:
        return [IntentType.OPEN_FILE, IntentType.SEARCH_FILES,
                IntentType.CREATE_FILE, IntentType.DELETE_FILE]

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        handlers = {
            IntentType.OPEN_FILE:    self._open_file,
            IntentType.SEARCH_FILES: self._search_files,
            IntentType.CREATE_FILE:  self._create_file,
            IntentType.DELETE_FILE:  self._delete_file,
        }
        handler = handlers.get(intent.type)
        if handler:
            return handler(intent, context)
        return ExecutionResult(success=False, message="Unknown file operation")

    def _open_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Open a file with the default system application."""
        filename = intent.parameters.get('filename', intent.parameters.get('selected', ''))
        if not filename:
            return ExecutionResult(success=False, message="No filename specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        # Search for the file
        matches = self._find_files(filename)

        if not matches:
            return ExecutionResult(
                success=False,
                message=f"File '{filename}' not found in allowed directories.",
                error_type=ErrorType.FILE_NOT_FOUND
            )

        if len(matches) == 1:
            return self._do_open(matches[0])

        # Multiple matches — ask for clarification
        options = [str(m) for m in matches[:5]]
        context.set_clarification(intent, options,
                                  f"I found {len(matches)} files. Which one?")
        formatted = "\n".join(f"  {i+1}. {p.name}" for i, p in enumerate(matches[:5]))
        return ExecutionResult(
            success=True,
            message=f"Which one?\n{formatted}",
            data={'results': options, 'requires_clarification': True}
        )

    def _do_open(self, filepath: Path) -> ExecutionResult:
        """Open a specific file with the system default handler."""
        try:
            os_name = get_os()
            if os_name == 'win':
                os.startfile(str(filepath))
            elif os_name == 'mac':
                subprocess.Popen(['open', str(filepath)])
            else:
                subprocess.Popen(['xdg-open', str(filepath)])

            return ExecutionResult(
                success=True,
                message=f"Opening {filepath.name}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Could not open file: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )

    def _search_files(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Search for files matching a query."""
        query = intent.parameters.get('query', '')
        if not query:
            return ExecutionResult(success=False, message="No search query specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        matches = self._find_files(query)

        if not matches:
            return ExecutionResult(
                success=True,
                message=f"No files found matching '{query}'.",
                data={'results': []}
            )

        results = [str(m) for m in matches[:10]]
        formatted = "\n".join(f"  {i+1}. {Path(r).name}" for i, r in enumerate(results))
        return ExecutionResult(
            success=True,
            message=f"Found {len(matches)} file(s):\n{formatted}",
            data={'results': results}
        )

    def _create_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Create a new file."""
        filename = intent.parameters.get('filename', '')
        if not filename:
            return ExecutionResult(success=False, message="No filename specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        # Create in first allowed directory (typically ~/Documents)
        target = self.allowed_dirs[0] / filename if self.allowed_dirs else Path.home() / filename

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
            return ExecutionResult(
                success=True,
                message=f"Created file: {target.name}",
                data={'path': str(target)}
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Could not create file: {e}",
                error_type=ErrorType.EXECUTION_FAILED
            )

    def _delete_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Delete a file (with confirmation via clarification)."""
        filename = intent.parameters.get('filename', intent.parameters.get('selected', ''))
        if not filename:
            return ExecutionResult(success=False, message="No filename specified.",
                                  error_type=ErrorType.INVALID_COMMAND)

        matches = self._find_files(filename)
        if not matches:
            return ExecutionResult(success=False,
                                  message=f"File '{filename}' not found.",
                                  error_type=ErrorType.FILE_NOT_FOUND)

        target = matches[0]

        # Check if pending confirmation
        pending = context.get_variable('pending_delete_path')
        if pending and str(target) == pending:
            try:
                target.unlink()
                context.set_variable('pending_delete_path', None)
                return ExecutionResult(success=True,
                                      message=f"Deleted {target.name}")
            except Exception as e:
                return ExecutionResult(success=False,
                                      message=f"Could not delete: {e}",
                                      error_type=ErrorType.EXECUTION_FAILED)

        # Require confirmation
        context.set_variable('pending_delete_path', str(target))
        context.set_clarification(
            intent, ['yes', 'no'],
            f"Are you sure you want to delete '{target.name}'?"
        )
        return ExecutionResult(
            success=True,
            message=f"Are you sure you want to delete '{target.name}'? Say yes or no.",
            data={'requires_clarification': True}
        )

    def _find_files(self, query: str) -> List[Path]:
        """Search for files matching query across allowed directories."""
        matches = []
        query_lower = query.lower().strip()

        for directory in self.allowed_dirs:
            if not directory.exists():
                continue
            try:
                for item in directory.rglob("*"):
                    if item.is_file() and query_lower in item.name.lower():
                        matches.append(item)
            except PermissionError:
                continue

        return sorted(matches, key=lambda p: p.name)
