"""
tests/test_nlp.py - Unit tests for NLP intent parsing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import IntentType, ConversationContext, Intent
from core.nlp import RuleBasedNLP


def setup_nlp():
    nlp = RuleBasedNLP()
    nlp.initialize()
    return nlp


def test_open_app():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("open chrome", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.OPEN_APP
    assert result.intent.parameters.get('app_name') == 'chrome'


def test_close_app():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("close firefox", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.CLOSE_APP


def test_volume_up():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("increase the volume", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.VOLUME_CONTROL
    assert result.intent.parameters.get('action') == 'up'


def test_volume_down():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("volume down", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.VOLUME_CONTROL
    assert result.intent.parameters.get('action') == 'down'


def test_screenshot():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("take a screenshot", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.SCREENSHOT


def test_search_files():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("find my python files", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.SEARCH_FILES


def test_help():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("help", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.HELP


def test_exit():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("exit", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.EXIT


def test_undo():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("undo", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.UNDO


def test_repeat():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("repeat", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.REPEAT


def test_unknown():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("blargle froop nonsense", ctx)
    assert result.intent.type == IntentType.UNKNOWN


def test_clarification_before_parse():
    """Verify NLP checks awaiting_clarification BEFORE fresh regex parse."""
    nlp = setup_nlp()
    ctx = ConversationContext()

    # Set up clarification state
    intent = Intent(type=IntentType.OPEN_FILE, confidence=0.6,
                    parameters={'filename': 'test'})
    ctx.set_clarification(intent, ['file1.txt', 'file2.txt'])

    # User responds with '1' — should resolve, NOT re-parse
    result = nlp.parse_intent("1", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.OPEN_FILE
    assert ctx.awaiting_clarification is False


def test_clarification_yes_confirmation():
    """Verify 'yes' confirms a confidence-floor match."""
    nlp = setup_nlp()
    ctx = ConversationContext()

    last_intent = Intent(type=IntentType.OPEN_APP, confidence=0.6,
                         parameters={'app_name': 'chrome'})
    ctx.set_clarification(last_intent, ['yes', 'no'])

    result = nlp.parse_intent("yes", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.OPEN_APP


def test_create_file():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("create a new file called notes.txt", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.CREATE_FILE


def test_lock_screen():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("lock the screen", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.LOCK_SCREEN


def test_system_info():
    nlp = setup_nlp()
    ctx = ConversationContext()
    result = nlp.parse_intent("show system info", ctx)
    assert result.intent is not None
    assert result.intent.type == IntentType.SYSTEM_INFO


if __name__ == '__main__':
    tests = [
        test_open_app, test_close_app, test_volume_up, test_volume_down,
        test_screenshot, test_search_files, test_help, test_exit,
        test_undo, test_repeat, test_unknown, test_clarification_before_parse,
        test_clarification_yes_confirmation, test_create_file,
        test_lock_screen, test_system_info,
    ]
    for test in tests:
        test()
        print(f"  ✓ {test.__name__}")
    print(f"✓ All {len(tests)} NLP tests passed!")
