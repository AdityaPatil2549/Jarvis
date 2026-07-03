# JARVIS-Lite

> Fully offline, privacy-first, voice-controlled desktop assistant.

**Whisper (STT) → Rule-Based NLP → Skill Execution → pyttsx3 (TTS)**

## Features

- **Push-to-talk voice input** via SPACE key
- **Text input** mode for typed commands
- **15 intent types**: file ops, app control, volume, screenshot, lock screen, system info, macros, undo/repeat
- **Conversation context** with multi-turn clarification flows
- **Barge-in support** — interrupt TTS mid-speech
- **Security** — path validation, dangerous command blocking, capability manifests
- **Macro system** — named command sequences from `config/macros.json`
- **UNDO/REPEAT** — reverse or re-execute last action
- **Pluggable skills** — install third-party skills from GitHub with isolated venvs

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run JARVIS
python main.py

# First run will launch a setup wizard.
```

## Command Examples

| Command | Action |
|---|---|
| `open chrome` | Launch Chrome |
| `find python files` | Search for files |
| `volume up` | Increase system volume |
| `take screenshot` | Capture screen |
| `lock screen` | Lock workstation |
| `system info` | Show CPU/RAM/Disk |
| `undo` | Reverse last action |
| `repeat` | Re-execute last command |
| `run morning routine` | Execute macro |
| `help` | Show all commands |
| `exit` | Shut down |

## CLI Flags

```
--verbose       Enable debug logging
--no-voice      Disable TTS output
--no-color      Disable colored output
--ascii         ASCII-only mode
--test-tts "Hello"  Test TTS and exit
--install-skill <URL>  Install a GitHub skill
```

## Architecture

```
main.py               ← Entry point
jarvis_engine.py       ← Orchestrator (state machine)
├── core/
│   ├── audio.py       ← SoundDevice capture
│   ├── stt.py         ← Whisper + Vosk fallback
│   ├── nlp.py         ← Rule-based intent parser
│   ├── tts.py         ← pyttsx3 with barge-in
│   ├── context.py     ← Session persistence + SQLite beliefs
│   ├── executor.py    ← Intent → Skill routing
│   ├── config_manager.py
│   ├── model_manager.py  ← VRAM orchestration
│   └── first_run_wizard.py
├── skills/
│   ├── base.py        ← Skill ABC
│   ├── manager.py     ← Auto-discovery & dispatch
│   ├── installer.py   ← Third-party installer
│   └── core/
│       ├── file_operations.py
│       ├── app_control.py
│       ├── system_control.py
│       ├── process_management.py
│       └── macro_skill.py
├── interface/
│   ├── ui.py          ← Terminal UI (ANSI colors, animations)
│   └── cli.py         ← Event loop
├── models/
│   └── __init__.py    ← All data models
├── utils/
│   ├── logger.py      ← Structured logging
│   ├── security.py    ← Path/command validation
│   └── helpers.py     ← OS detection, formatting
├── config/
│   ├── settings.json  ← System configuration
│   └── macros.json    ← Named command sequences
└── tests/
    ├── test_models.py
    ├── test_nlp.py
    └── test_security.py
```

## Tests

```bash
python tests/test_models.py    # 11 tests
python tests/test_nlp.py       # 16 tests
python tests/test_security.py  #  7 tests
```

## Tech Stack

| Component | Technology |
|---|---|
| STT | OpenAI Whisper (base) |
| NLP | Rule-based regex (Phase 1) |
| TTS | pyttsx3 (SAPI5/espeak) |
| Audio | sounddevice |
| UI | ANSI terminal |
| Config | JSON |
| Memory | SQLite (core beliefs) |

## License

MIT
