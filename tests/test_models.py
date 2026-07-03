"""
tests/test_models.py - Unit tests for core data models.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import (
    State, IntentType, ErrorType, AudioFormat,
    AudioConfig, Intent, IntentParseResult, ExecutionResult,
    ConversationTurn, ConversationContext, SkillManifest,
    SkillMetadata, SystemConfig, JarvisError
)


def test_state_enum():
    """Test all 10 states exist."""
    assert len(State) == 10
    assert State.INITIALIZING.value == "initializing"
    assert State.IDLE.value == "idle"
    assert State.SHUTTING_DOWN.value == "shutting_down"


def test_intent_type_enum():
    """Test all 16 intent types exist."""
    assert len(IntentType) == 16
    assert IntentType.UNDO.value == "undo"
    assert IntentType.REPEAT.value == "repeat"
    assert IntentType.MACRO.value == "macro"
    assert IntentType.UNKNOWN.value == "unknown"


def test_intent_serialization():
    """Test Intent to_dict / from_dict roundtrip."""
    intent = Intent(type=IntentType.OPEN_APP, confidence=0.95,
                    parameters={'app_name': 'chrome'}, raw_text='open chrome')
    d = intent.to_dict()
    restored = Intent.from_dict(d)
    assert restored.type == IntentType.OPEN_APP
    assert restored.confidence == 0.95
    assert restored.parameters['app_name'] == 'chrome'


def test_intent_parse_result_post_init():
    """Test that intents list is auto-populated."""
    intent = Intent(type=IntentType.HELP, confidence=0.9)
    result = IntentParseResult(intent=intent)
    assert len(result.intents) == 1
    assert result.intents[0] is intent


def test_conversation_context_add_turn():
    """Test add_turn with auto-pruning."""
    ctx = ConversationContext()
    for i in range(60):
        ctx.add_turn('user', f'message {i}')
    assert len(ctx.history) == 50
    assert ctx.history[0].content == 'message 10'


def test_conversation_context_variables():
    """Test context variable get/set."""
    ctx = ConversationContext()
    ctx.set_variable('last_search_results', ['/a.txt', '/b.txt'])
    assert ctx.get_variable('last_search_results') == ['/a.txt', '/b.txt']
    assert ctx.get_variable('nonexistent', 'default') == 'default'


def test_conversation_context_clarification():
    """Test clarification state management."""
    ctx = ConversationContext()
    intent = Intent(type=IntentType.OPEN_FILE, confidence=0.6)
    ctx.set_clarification(intent, ['file1.txt', 'file2.txt'])
    assert ctx.awaiting_clarification is True
    assert len(ctx.clarification_options) == 2
    ctx.clear_clarification()
    assert ctx.awaiting_clarification is False
    assert len(ctx.clarification_options) == 0


def test_conversation_context_reset():
    """Test full context reset."""
    ctx = ConversationContext()
    ctx.add_turn('user', 'hello')
    ctx.set_variable('key', 'value')
    ctx.reset()
    assert len(ctx.history) == 0
    assert len(ctx.variables) == 0
    assert ctx.last_intent is None


def test_system_config_roundtrip():
    """Test SystemConfig to_dict / from_dict."""
    config = SystemConfig(stt_model='small', tts_rate=200, verbose_logging=True)
    d = config.to_dict()
    restored = SystemConfig.from_dict(d)
    assert restored.stt_model == 'small'
    assert restored.tts_rate == 200
    assert restored.verbose_logging is True


def test_execution_result():
    """Test ExecutionResult serialization."""
    result = ExecutionResult(success=True, message='Done',
                             error_type=None, data={'key': 'val'})
    d = result.to_dict()
    assert d['success'] is True
    assert d['error_type'] is None
    assert d['data']['key'] == 'val'


if __name__ == '__main__':
    test_state_enum()
    test_intent_type_enum()
    test_intent_serialization()
    test_intent_parse_result_post_init()
    test_conversation_context_add_turn()
    test_conversation_context_variables()
    test_conversation_context_clarification()
    test_conversation_context_reset()
    test_system_config_roundtrip()
    test_execution_result()
    print("✓ All model tests passed!")
