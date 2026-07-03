"""
core/first_run_wizard.py - First-run setup wizard for JARVIS-Lite.
Runs when config/settings.json is missing.

Source of truth: Implementation_plan.md §3.11
"""

import json
from pathlib import Path


def run_setup_wizard():
    """Guided CLI wizard for first-time setup."""

    print("\n" + "=" * 60)
    print("  Welcome to JARVIS-Lite Setup")
    print("=" * 60)
    print()

    # 1. Push-to-talk key
    print("[1/4] Push-to-Talk Key")
    print("  Default: SPACE")
    ptt_key = input("  Enter key (or press Enter for default): ").strip()
    if not ptt_key:
        ptt_key = "space"
    print()

    # 2. STT model size
    print("[2/4] Speech Recognition Model")
    print("  Options: tiny (fastest), base (recommended), small (most accurate)")
    stt_model = input("  Enter model size (default: base): ").strip().lower()
    if stt_model not in ('tiny', 'base', 'small', 'medium'):
        stt_model = "base"
    print()

    # 3. Trusted directories
    print("[3/4] Trusted Directories")
    print("  JARVIS can only access files in these directories.")
    print("  Default: ~/Documents, ~/Desktop, ~/Downloads")
    custom_dirs = input("  Add custom directory (or Enter for defaults): ").strip()
    allowed_dirs = ["~/Documents", "~/Desktop", "~/Downloads"]
    if custom_dirs:
        allowed_dirs.append(custom_dirs)
    print()

    # 4. Verbose logging
    print("[4/4] Verbose Logging")
    verbose = input("  Enable verbose logging? (y/N): ").strip().lower()
    verbose_logging = verbose in ('y', 'yes')
    print()

    # Generate config
    config = {
        "pipeline": {
            "stt": {
                "engine": "whisper",
                "model": stt_model,
                "fallback": "vosk",
                "language": "en"
            },
            "nlp": {
                "engine": "spacy",
                "model": "en_core_web_sm",
                "confidence_threshold": 0.8
            },
            "tts": {
                "engine": "pyttsx3",
                "rate": 175,
                "volume": 0.9
            }
        },
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "chunk_size": 1024,
            "silence_threshold": 0.01,
            "silence_duration_ms": 800,
            "max_recording_seconds": 10
        },
        "features": {
            "wake_word_enabled": False,
            "save_history": True,
            "verbose_logging": verbose_logging,
            "push_to_talk_key": ptt_key
        },
        "skills": {
            "file_operations": {
                "enabled": True,
                "allowed_directories": allowed_dirs
            },
            "app_control": {
                "enabled": True,
                "app_map": {
                    "chrome": {"win": "chrome", "mac": "Google Chrome", "linux": "google-chrome"},
                    "firefox": {"win": "firefox", "mac": "Firefox", "linux": "firefox"},
                    "vscode": {"win": "code", "mac": "Visual Studio Code", "linux": "code"},
                    "terminal": {"win": "cmd", "mac": "Terminal", "linux": "gnome-terminal"},
                    "notepad": {"win": "notepad", "mac": "TextEdit", "linux": "gedit"},
                    "explorer": {"win": "explorer", "mac": "Finder", "linux": "nautilus"}
                }
            },
            "system_control": {"enabled": True, "screenshot_dir": "~/Desktop"},
            "process_management": {"enabled": True}
        },
        "hotkeys": {
            "push_to_talk": ptt_key,
            "cancel": "escape",
            "help": "f1",
            "exit": "ctrl+q"
        }
    }

    # Write config
    config_path = Path("config/settings.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    print("=" * 60)
    print(f"  ✓ Configuration saved to {config_path}")
    print("  ✓ Setup complete. You're ready to go!")
    print("=" * 60)
    print()
