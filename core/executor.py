"""
core/executor.py - Command execution for JARVIS-Lite.
Routes intents to skills and handles UNDO/REPEAT inline.

Source of truth: Backend_schema.md §3.5, Implementation_plan.md §3.9
"""

import time
from abc import ABC, abstractmethod
from typing import Optional, Dict

from models import (
    Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
)
from utils.security import validate_safe_execution
from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# INTENT → SKILL ROUTING TABLE
# ============================================================================

INTENT_SKILL_MAP: Dict[IntentType, Optional[str]] = {
    IntentType.OPEN_FILE:       "file_operations",
    IntentType.SEARCH_FILES:    "file_operations",
    IntentType.CREATE_FILE:     "file_operations",
    IntentType.DELETE_FILE:     "file_operations",
    IntentType.OPEN_APP:        "app_control",
    IntentType.CLOSE_APP:       "app_control",
    IntentType.VOLUME_CONTROL:  "system_control",
    IntentType.SCREENSHOT:      "system_control",
    IntentType.LOCK_SCREEN:     "system_control",
    IntentType.SYSTEM_INFO:     "process_management",
    IntentType.HELP:            None,   # Handled inline
    IntentType.EXIT:            None,   # Handled inline
    IntentType.UNDO:            None,   # Handled inline by executor
    IntentType.REPEAT:          None,   # Handled inline by executor
    IntentType.MACRO:           "macro_skill",
    IntentType.UNKNOWN:         None,
}


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class ExecutorInterface(ABC):
    """Abstract interface for command execution."""

    @abstractmethod
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        pass


# ============================================================================
# SKILL-BASED EXECUTOR
# ============================================================================

class SkillBasedExecutor(ExecutorInterface):
    """Routes intents to registered skills and handles meta-intents inline."""

    def __init__(self, skill_manager=None):
        self.skill_manager = skill_manager

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Execute an intent through the skill system.

        Flow:
        1. Security check
        2. Handle UNDO/REPEAT inline
        3. Route to skill via INTENT_SKILL_MAP
        4. Execute with timeout tracking
        5. Write context variables after success
        """
        start_time = time.time()

        # ── Step 1: Security check ─────────────────────────────────────
        if not validate_safe_execution(intent):
            return ExecutionResult(
                success=False,
                message="Command blocked for safety.",
                error_type=ErrorType.PERMISSION_DENIED,
                duration=time.time() - start_time
            )

        # ── Step 2: Handle UNDO inline ─────────────────────────────────
        if intent.type == IntentType.UNDO:
            return self._handle_undo(context, start_time)

        # ── Step 3: Handle REPEAT inline ───────────────────────────────
        if intent.type == IntentType.REPEAT:
            return self._handle_repeat(context, start_time)

        # ── Step 4: Route to skill ─────────────────────────────────────
        skill_name = INTENT_SKILL_MAP.get(intent.type)
        if skill_name is None:
            # HELP, EXIT, UNKNOWN handled by engine, not executor
            return ExecutionResult(
                success=False,
                message=f"No handler for intent: {intent.type.value}",
                error_type=ErrorType.INVALID_COMMAND,
                duration=time.time() - start_time
            )

        if self.skill_manager is None:
            return ExecutionResult(
                success=False,
                message="Skill manager not available.",
                error_type=ErrorType.SYSTEM_ERROR,
                duration=time.time() - start_time
            )

        # ── Step 5: Dispatch to skill manager ──────────────────────────
        result = self.skill_manager.dispatch(intent, context)

        if result is None:
            result = ExecutionResult(
                success=False,
                message=f"Skill '{skill_name}' not found or failed.",
                error_type=ErrorType.EXECUTION_FAILED,
                duration=time.time() - start_time
            )
        else:
            result.duration = time.time() - start_time

        # ── Step 6: Context variable writes (after success) ────────────
        if result.success:
            context.last_intent = intent

            # Write context variables based on intent type
            if intent.type == IntentType.SEARCH_FILES and result.data:
                context.set_variable('last_search_results',
                                     result.data.get('results', []))
            elif intent.type == IntentType.OPEN_FILE:
                context.set_variable('last_opened_file',
                                     intent.parameters.get('filename', ''))
            elif intent.type == IntentType.OPEN_APP:
                context.set_variable('last_opened_app',
                                     intent.parameters.get('app_name', ''))

        logger.debug(
            f"Executed {intent.type.value}: success={result.success} "
            f"({result.duration:.3f}s)",
            component="executor"
        )

        return result

    def _handle_undo(self, context: ConversationContext, start_time: float) -> ExecutionResult:
        """Handle UNDO intent by reversing the last reversible action."""
        last = context.last_intent
        if last is None:
            return ExecutionResult(
                success=False,
                message="Nothing to undo.",
                duration=time.time() - start_time
            )

        # Only certain intents are reversible
        if last.type == IntentType.OPEN_APP:
            # Reverse: close the app
            close_intent = Intent(
                type=IntentType.CLOSE_APP,
                confidence=1.0,
                parameters=last.parameters,
                raw_text=f"undo: close {last.parameters.get('app_name', '')}"
            )
            if self.skill_manager:
                result = self.skill_manager.dispatch(close_intent, context)
                if result and result.success:
                    context.last_intent = None
                    return ExecutionResult(
                        success=True,
                        message=f"Undone: closed {last.parameters.get('app_name', 'app')}.",
                        duration=time.time() - start_time
                    )

        elif last.type == IntentType.CREATE_FILE:
            # Reverse: delete the created file
            delete_intent = Intent(
                type=IntentType.DELETE_FILE,
                confidence=1.0,
                parameters=last.parameters,
                raw_text=f"undo: delete {last.parameters.get('filename', '')}"
            )
            if self.skill_manager:
                result = self.skill_manager.dispatch(delete_intent, context)
                if result and result.success:
                    context.last_intent = None
                    return ExecutionResult(
                        success=True,
                        message=f"Undone: deleted {last.parameters.get('filename', 'file')}.",
                        duration=time.time() - start_time
                    )

        return ExecutionResult(
            success=False,
            message=f"Cannot undo '{last.type.value}' — not a reversible action.",
            duration=time.time() - start_time
        )

    def _handle_repeat(self, context: ConversationContext, start_time: float) -> ExecutionResult:
        """Handle REPEAT intent by re-executing the last intent."""
        last = context.last_intent
        if last is None:
            return ExecutionResult(
                success=False,
                message="Nothing to repeat.",
                duration=time.time() - start_time
            )

        logger.info(f"Repeating: {last.type.value}", component="executor")
        return self.execute(last, context)
