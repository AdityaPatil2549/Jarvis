"""
tests/test_model_manager.py - Unit tests for VRAM orchestration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.model_manager import ModelManager


def test_initialization_no_torch():
    """Test model manager initializes gracefully when torch is missing."""
    mm = ModelManager()
    mm.initialize()
    assert mm._vram_managed is False
    assert mm.current_state == "IDLE"


def test_vram_management_disabled():
    """When VRAM management is disabled, state remains IDLE."""
    mm = ModelManager()
    mm._vram_managed = False

    mm.prepare_for_stt()
    assert mm.current_state == "IDLE"

    mm.prepare_for_nlp()
    assert mm.current_state == "IDLE"


def test_vram_management_enabled():
    """When VRAM management is enabled, states transition correctly."""
    mm = ModelManager()
    mm._vram_managed = True
    mm._current_state = "IDLE"

    mm.prepare_for_stt()
    assert mm.current_state == "STT_READY"

    mm.prepare_for_nlp()
    assert mm.current_state == "NLP_READY"

    mm.unload_all()
    assert mm.current_state == "IDLE"


if __name__ == '__main__':
    tests = [
        test_initialization_no_torch,
        test_vram_management_disabled,
        test_vram_management_enabled,
    ]
    for test in tests:
        test()
        print(f"  ✓ {test.__name__}")
    print(f"✓ All {len(tests)} ModelManager tests passed!")
