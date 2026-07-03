"""
tests/test_config.py - Unit tests for configuration loading.
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.config_manager import ConfigManager


def test_load_valid_config():
    """Load a valid settings.json and verify fields."""
    # Create temp config
    config_data = {
        "pipeline": {
            "stt": {"engine": "faster-whisper", "model": "small"},
            "nlp": {"engine": "spacy", "model": "en_core_web_sm"},
            "tts": {"engine": "kokoro", "voice": "af_sky", "lang_code": "b",
                    "rate": 200, "volume": 0.8}
        },
        "features": {"verbose_logging": True, "save_history": False}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        tmp_path = f.name

    try:
        cm = ConfigManager(config_path=tmp_path)
        config = cm.load_all()

        assert config.stt_engine == "faster-whisper"
        assert config.stt_model == "small"
        assert config.tts_engine == "kokoro"
        assert config.tts_voice == "af_sky"
        assert config.tts_lang_code == "b"
        assert config.tts_rate == 200
        assert config.tts_volume == 0.8
        assert config.verbose_logging is True
        assert config.save_history is False
    finally:
        os.unlink(tmp_path)


def test_missing_config_uses_defaults():
    """Missing config file should produce valid defaults."""
    cm = ConfigManager(config_path="nonexistent_file.json")
    config = cm.load_all()

    assert config.stt_engine == "faster-whisper"
    assert config.stt_model == "base"
    assert config.tts_engine == "kokoro"
    assert config.tts_voice == "af_heart"
    assert config.tts_lang_code == "a"
    assert config.verbose_logging is False


def test_dot_notation_access():
    """Test dot-notation config access."""
    cm = ConfigManager()
    cm.config = {
        "pipeline": {
            "stt": {"engine": "faster-whisper", "model": "base"}
        }
    }

    assert cm.get("pipeline.stt.engine") == "faster-whisper"
    assert cm.get("pipeline.stt.model") == "base"
    assert cm.get("pipeline.stt.nonexistent", "default") == "default"
    assert cm.get("nonexistent.path", "fallback") == "fallback"


def test_macros_loading():
    """Test macro loading."""
    macro_data = {
        "test_macro": [
            {"intent": "open_app", "entity": "chrome"}
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(macro_data, f)
        tmp_path = f.name

    try:
        cm = ConfigManager()
        cm.MACRO_FILE = __import__('pathlib').Path(tmp_path)
        cm._load_macros()

        assert "test_macro" in cm.macros
        assert len(cm.macros["test_macro"]) == 1
        assert cm.get_macro("test_macro")[0]["intent"] == "open_app"
        assert cm.get_macro("nonexistent") is None
    finally:
        os.unlink(tmp_path)


if __name__ == '__main__':
    tests = [
        test_load_valid_config, test_missing_config_uses_defaults,
        test_dot_notation_access, test_macros_loading,
    ]
    for test in tests:
        test()
        print(f"  + {test.__name__}")
    print(f"+ All {len(tests)} config tests passed!")
