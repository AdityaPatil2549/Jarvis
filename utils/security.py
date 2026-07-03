"""
utils/security.py - Security validation for commands before execution.
Prevents directory traversal, dangerous commands, and prompt injection.

Source of truth: Implementation_plan.md §3.3, Architecture_Enhancements.md §2
"""

import re
from pathlib import Path
from typing import Optional, List


# ============================================================================
# DANGEROUS COMMAND PATTERNS
# ============================================================================

DANGEROUS_PATTERNS = [
    r'\.\.',             # Directory traversal
    r'rm\s+-rf',         # Recursive delete
    r'del\s+/[sf]',     # Windows force delete
    r'format\s+[a-z]:',  # Disk format
    r'mkfs\.',           # Linux format
    r'eval\(',           # Code execution
    r'exec\(',           # Code execution
    r'__import__',       # Dynamic import
    r'sudo\s+',          # Privilege escalation
    r'powershell\s+-enc', # Encoded powershell
    r'reg\s+delete',     # Registry deletion
]

# Capabilities that intents may require
INTENT_CAPABILITY_MAP = {
    'open_file':       ['file_system_read'],
    'search_files':    ['file_system_read'],
    'create_file':     ['file_system_write'],
    'delete_file':     ['file_system_write'],
    'open_app':        ['process_exec'],
    'close_app':       ['process_exec'],
    'volume_control':  ['system_control'],
    'screenshot':      ['system_control'],
    'lock_screen':     ['system_control'],
    'system_info':     ['system_control'],
}


# ============================================================================
# PATH VALIDATION
# ============================================================================

def validate_file_path(path: str, allowed_dirs: List[str]) -> Optional[str]:
    """
    Validate file path is within allowed directories.

    Args:
        path: File path to validate
        allowed_dirs: List of allowed base directories

    Returns:
        Resolved path string if valid, None if blocked
    """
    try:
        resolved = Path(path).expanduser().resolve()

        # Check for directory traversal
        if '..' in str(path):
            return None

        # Check if path is within allowed directories
        for allowed in allowed_dirs:
            allowed_resolved = Path(allowed).expanduser().resolve()
            try:
                resolved.relative_to(allowed_resolved)
                return str(resolved)
            except ValueError:
                continue

        return None
    except (OSError, ValueError):
        return None


# ============================================================================
# COMMAND VALIDATION
# ============================================================================

def sanitize_command_text(text: str) -> str:
    """
    Sanitize command text to prevent injection.
    Returns cleaned text.
    """
    # Strip control characters
    cleaned = ''.join(c for c in text if c.isprintable() or c in ('\n', '\t'))

    # Limit length
    cleaned = cleaned[:500]

    return cleaned.strip()


def is_dangerous_command(text: str) -> bool:
    """Check if command matches dangerous patterns."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in DANGEROUS_PATTERNS)


# ============================================================================
# CAPABILITY MANIFEST VALIDATION
# ============================================================================

def validate_capabilities(skill, intent) -> bool:
    """
    Check if a skill's manifest permits executing the given intent.

    Args:
        skill: Skill instance (must have .manifest attribute or None for core skills)
        intent: Intent instance with .type attribute

    Returns:
        True if allowed, False if denied
    """
    # Core skills (no manifest) are always allowed
    manifest = getattr(skill, 'manifest', None)
    if manifest is None:
        return True

    # Get required capabilities for this intent type
    required = INTENT_CAPABILITY_MAP.get(intent.type.value, [])
    if not required:
        # No capabilities required for this intent type
        return True

    # Check if skill manifest declares all required capabilities
    skill_capabilities = getattr(manifest, 'capabilities', [])
    for cap in required:
        if cap not in skill_capabilities:
            return False

    return True


def validate_safe_execution(intent) -> bool:
    """
    Pre-execution safety check for an intent.

    Returns True if the intent is safe to execute.
    """
    # Check raw text for dangerous patterns
    raw_text = getattr(intent, 'raw_text', '')
    if raw_text and is_dangerous_command(raw_text):
        return False

    # Check parameters for path traversal
    params = getattr(intent, 'parameters', {})
    for key, value in params.items():
        if isinstance(value, str) and '..' in value:
            return False

    return True
