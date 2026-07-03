"""
tests/test_skills.py - Unit tests for skill manager and core skills.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Intent, IntentType, ConversationContext, ExecutionResult
from skills.base import BaseSkill
from skills.manager import SkillManager


# ============================================================================
# MOCK SKILL FOR TESTING
# ============================================================================

class MockSkill(BaseSkill):
    name = "mock_skill"
    version = "1.0.0"
    description = "Test skill"

    def initialize(self):
        return True

    def get_handled_intents(self):
        return [IntentType.HELP]

    def execute(self, intent, context):
        return ExecutionResult(success=True, message="Mock executed!")


class FailSkill(BaseSkill):
    name = "fail_skill"
    version = "1.0.0"
    description = "Always fails init"

    def initialize(self):
        return False

    def get_handled_intents(self):
        return [IntentType.SYSTEM_INFO]

    def execute(self, intent, context):
        return ExecutionResult(success=False, message="Should never run")


# ============================================================================
# TESTS
# ============================================================================

def test_skill_registration():
    """Registering a skill makes it dispatchable."""
    sm = SkillManager()
    skill = MockSkill()
    skill.initialize()
    sm._register_skill(skill)

    assert "mock_skill" in sm.skills
    assert sm._intent_map[IntentType.HELP] == "mock_skill"


def test_skill_dispatch():
    """Dispatching an intent routes to correct skill."""
    sm = SkillManager()
    skill = MockSkill()
    skill.initialize()
    sm._register_skill(skill)

    ctx = ConversationContext()
    intent = Intent(type=IntentType.HELP, confidence=1.0)
    result = sm.dispatch(intent, ctx)

    assert result is not None
    assert result.success is True
    assert result.message == "Mock executed!"


def test_dispatch_unregistered_returns_none():
    """Dispatching unregistered intent returns None."""
    sm = SkillManager()
    ctx = ConversationContext()
    intent = Intent(type=IntentType.OPEN_APP, confidence=0.9)
    result = sm.dispatch(intent, ctx)
    assert result is None


def test_get_all_metadata():
    """Metadata returns info for all registered skills."""
    sm = SkillManager()
    skill = MockSkill()
    skill.initialize()
    sm._register_skill(skill)

    meta = sm.get_all_metadata()
    assert len(meta) == 1
    assert meta[0]['name'] == "mock_skill"
    assert meta[0]['version'] == "1.0.0"


def test_skill_exception_handling():
    """Skill that raises exception returns error result."""

    class BrokenSkill(BaseSkill):
        name = "broken"
        version = "1.0.0"
        description = "Breaks on execute"

        def initialize(self):
            return True

        def get_handled_intents(self):
            return [IntentType.LOCK_SCREEN]

        def execute(self, intent, context):
            raise RuntimeError("Skill crashed!")

    sm = SkillManager()
    skill = BrokenSkill()
    skill.initialize()
    sm._register_skill(skill)

    ctx = ConversationContext()
    intent = Intent(type=IntentType.LOCK_SCREEN, confidence=1.0, raw_text="lock")
    result = sm.dispatch(intent, ctx)

    assert result is not None
    assert result.success is False
    assert "Skill crashed!" in result.message


def test_shutdown():
    """Shutdown should not raise."""
    sm = SkillManager()
    skill = MockSkill()
    skill.initialize()
    sm._register_skill(skill)
    sm.shutdown()  # Should not raise


if __name__ == '__main__':
    tests = [
        test_skill_registration, test_skill_dispatch,
        test_dispatch_unregistered_returns_none, test_get_all_metadata,
        test_skill_exception_handling, test_shutdown,
    ]
    for test in tests:
        test()
        print(f"  + {test.__name__}")
    print(f"+ All {len(tests)} skill tests passed!")
