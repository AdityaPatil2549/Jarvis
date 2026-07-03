"""
skills/core/macro_skill.py - Macro execution skill.
Handles: MACRO — runs named sequences from config/macros.json

Source of truth: Implementation_plan.md §4.7
"""

from typing import List

from models import Intent, IntentType, ExecutionResult, ErrorType, ConversationContext
from skills.base import BaseSkill
from utils.logger import JarvisLogger


logger = JarvisLogger()


class MacroSkill(BaseSkill):
    """Executes named macro sequences from config/macros.json."""

    name = "macro_skill"
    version = "1.0.0"
    description = "Execute named command sequences (macros)"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.macros = {}
        self._executor = None  # Set by engine after init

    def initialize(self) -> bool:
        return True

    def set_executor(self, executor):
        """Inject the executor for recursive intent execution."""
        self._executor = executor

    def set_macros(self, macros: dict):
        """Load macros from config manager."""
        self.macros = macros
        logger.debug(f"MacroSkill loaded {len(macros)} macros", component="skills")

    def get_handled_intents(self) -> List[IntentType]:
        return [IntentType.MACRO]

    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Execute a macro by name.
        1. Look up macro by intent.parameters['macro_name'] in macros dict
        2. For each step, construct a sub-intent and execute
        """
        macro_name = intent.parameters.get('macro_name', '')

        # Try to find macro (case-insensitive)
        macro_steps = None
        for name, steps in self.macros.items():
            if name.lower() == macro_name.lower():
                macro_steps = steps
                macro_name = name
                break

        if macro_steps is None:
            available = ', '.join(self.macros.keys()) if self.macros else 'none'
            return ExecutionResult(
                success=False,
                message=f"Macro '{macro_name}' not found. Available: {available}",
                error_type=ErrorType.INVALID_COMMAND
            )

        if self._executor is None:
            return ExecutionResult(
                success=False,
                message="Macro executor not configured.",
                error_type=ErrorType.SYSTEM_ERROR
            )

        # Execute each step
        results = []
        for i, step in enumerate(macro_steps):
            try:
                intent_type = IntentType(step.get('intent', 'unknown'))
                sub_intent = Intent(
                    type=intent_type,
                    confidence=1.0,
                    parameters={'app_name': step.get('entity', ''),
                                'filename': step.get('entity', '')},
                    raw_text=f"macro step {i+1}: {step}"
                )
                result = self._executor.execute(sub_intent, context)
                results.append(f"  {i+1}. {result.message}")
            except Exception as e:
                results.append(f"  {i+1}. Failed: {e}")

        summary = "\n".join(results)
        return ExecutionResult(
            success=True,
            message=f"Macro '{macro_name}' completed:\n{summary}"
        )
