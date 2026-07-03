"""
tests/test_executor.py - Unit tests for the command executor.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import (
    Intent, IntentType, ConversationContext, ExecutionResult, ErrorType
)
from core.executor import SkillBasedExecutor, INTENT_SKILL_MAP


def test_undo_nothing():
    """UNDO with no prior action returns failure."""
    executor = SkillBasedExecutor(skill_manager=None)
    ctx = ConversationContext()
    intent = Intent(type=IntentType.UNDO, confidence=1.0)
    result = executor.execute(intent, ctx)
    assert result.success is False
    assert "Nothing to undo" in result.message


def test_repeat_nothing():
    """REPEAT with no prior action returns failure."""
    executor = SkillBasedExecutor(skill_manager=None)
    ctx = ConversationContext()
    intent = Intent(type=IntentType.REPEAT, confidence=1.0)
    result = executor.execute(intent, ctx)
    assert result.success is False
    assert "Nothing to repeat" in result.message


def test_no_skill_manager():
    """Routing intent with no skill manager returns system error."""
    executor = SkillBasedExecutor(skill_manager=None)
    ctx = ConversationContext()
    intent = Intent(type=IntentType.OPEN_APP, confidence=0.95)
    result = executor.execute(intent, ctx)
    assert result.success is False
    assert result.error_type == ErrorType.SYSTEM_ERROR


def test_dangerous_blocked():
    """Dangerous raw_text should be blocked by security."""
    executor = SkillBasedExecutor(skill_manager=None)
    ctx = ConversationContext()
    intent = Intent(type=IntentType.OPEN_APP, confidence=0.95,
                    raw_text="rm -rf /")
    result = executor.execute(intent, ctx)
    assert result.success is False
    assert result.error_type == ErrorType.PERMISSION_DENIED


def test_help_exit_no_handler():
    """HELP and EXIT have no handler — executor returns INVALID_COMMAND."""
    executor = SkillBasedExecutor(skill_manager=None)
    ctx = ConversationContext()

    for intent_type in [IntentType.HELP, IntentType.EXIT, IntentType.UNKNOWN]:
        intent = Intent(type=intent_type, confidence=1.0)
        result = executor.execute(intent, ctx)
        assert result.success is False


def test_intent_skill_map_complete():
    """Every IntentType must have an entry in INTENT_SKILL_MAP."""
    for it in IntentType:
        assert it in INTENT_SKILL_MAP, f"{it.value} missing from INTENT_SKILL_MAP"


def test_context_updated_on_success():
    """Executor writes context variables after success."""

    class MockSkillManager:
        def dispatch(self, intent, context):
            return ExecutionResult(
                success=True,
                message="Done",
                data={'results': ['a.txt', 'b.txt']}
            )

    executor = SkillBasedExecutor(skill_manager=MockSkillManager())
    ctx = ConversationContext()

    intent = Intent(type=IntentType.SEARCH_FILES, confidence=0.9,
                    parameters={'query': 'test'}, raw_text="find test")
    result = executor.execute(intent, ctx)

    assert result.success is True
    assert ctx.last_intent is intent
    assert ctx.get_variable('last_search_results') == ['a.txt', 'b.txt']


if __name__ == '__main__':
    tests = [
        test_undo_nothing, test_repeat_nothing, test_no_skill_manager,
        test_dangerous_blocked, test_help_exit_no_handler,
        test_intent_skill_map_complete, test_context_updated_on_success,
    ]
    for test in tests:
        test()
        print(f"  + {test.__name__}")
    print(f"+ All {len(tests)} executor tests passed!")
