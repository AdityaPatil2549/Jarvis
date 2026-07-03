"""
tests/test_security.py - Unit tests for security module.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.security import (
    is_dangerous_command, validate_file_path, sanitize_command_text,
    validate_capabilities, validate_safe_execution
)
from models import Intent, IntentType, SkillManifest


def test_dangerous_commands():
    """Test dangerous command detection."""
    assert is_dangerous_command("rm -rf /") is True
    assert is_dangerous_command("open chrome") is False
    assert is_dangerous_command("del /s /q C:\\") is True
    assert is_dangerous_command("format c:") is True
    assert is_dangerous_command("eval(code)") is True
    assert is_dangerous_command("open vscode") is False
    assert is_dangerous_command("sudo rm something") is True
    assert is_dangerous_command("find my files") is False


def test_path_validation():
    """Test path validation against allowed dirs."""
    import tempfile
    import pathlib

    # Create a temp dir structure
    tmp = tempfile.mkdtemp()
    allowed = [tmp]

    # Valid path
    valid = os.path.join(tmp, "test.txt")
    result = validate_file_path(valid, allowed)
    assert result is not None

    # Traversal attack
    traversal = os.path.join(tmp, "..", "..", "etc", "passwd")
    result = validate_file_path(traversal, allowed)
    assert result is None

    # Path outside allowed dirs
    outside = "/root/secret.txt"
    result = validate_file_path(outside, allowed)
    assert result is None

    # Cleanup
    os.rmdir(tmp)


def test_sanitize_text():
    """Test command text sanitization."""
    # Normal text
    assert sanitize_command_text("open chrome") == "open chrome"

    # Strip control characters
    result = sanitize_command_text("open\x00chrome")
    assert '\x00' not in result

    # Length limit
    long_text = "a" * 1000
    result = sanitize_command_text(long_text)
    assert len(result) <= 500


def test_manifest_permission_denied():
    """Test capability manifest enforcement."""

    class MockSkill:
        manifest = SkillManifest(name="mock", version="1.0",
                                 capabilities=["network"],
                                 entry_point="main.py")

    intent = Intent(type=IntentType.CREATE_FILE, confidence=0.9)
    # CREATE_FILE requires 'file_system_write', but skill only has 'network'
    assert validate_capabilities(MockSkill(), intent) is False


def test_manifest_permission_allowed():
    """Test capability manifest allows matching capabilities."""

    class MockSkill:
        manifest = SkillManifest(name="mock", version="1.0",
                                 capabilities=["file_system_write"],
                                 entry_point="main.py")

    intent = Intent(type=IntentType.CREATE_FILE, confidence=0.9)
    assert validate_capabilities(MockSkill(), intent) is True


def test_core_skill_always_allowed():
    """Core skills (no manifest) are always allowed."""

    class CoreSkill:
        manifest = None  # Core skills have no manifest

    intent = Intent(type=IntentType.CREATE_FILE, confidence=0.9)
    assert validate_capabilities(CoreSkill(), intent) is True


def test_validate_safe_execution():
    """Test pre-execution safety."""
    # Safe intent
    safe = Intent(type=IntentType.OPEN_APP, confidence=0.9,
                  raw_text="open chrome")
    assert validate_safe_execution(safe) is True

    # Dangerous intent
    danger = Intent(type=IntentType.OPEN_APP, confidence=0.9,
                    raw_text="rm -rf /")
    assert validate_safe_execution(danger) is False

    # Path traversal in params
    traversal = Intent(type=IntentType.OPEN_FILE, confidence=0.9,
                       parameters={'filename': '../../etc/passwd'})
    assert validate_safe_execution(traversal) is False


if __name__ == '__main__':
    tests = [
        test_dangerous_commands, test_path_validation, test_sanitize_text,
        test_manifest_permission_denied, test_manifest_permission_allowed,
        test_core_skill_always_allowed, test_validate_safe_execution,
    ]
    for test in tests:
        test()
        print(f"  ✓ {test.__name__}")
    print(f"✓ All {len(tests)} security tests passed!")
