# JARVIS-Lite: Complete Implementation Plan

**Version:** 1.0  
**Based On:** PRD v1.0, Backend Schema v1.0, Appflow Spec, Frontend Guidelines v1.0, Tech Stack Spec  
**Target Platform:** Windows 10/11 (primary), macOS, Linux  
**Python:** 3.11+  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Phase 1 — Foundation & Project Scaffold](#2-phase-1--foundation--project-scaffold)
3. [Phase 2 — Core Engine Modules](#3-phase-2--core-engine-modules)
4. [Phase 3 — Skills Layer](#4-phase-3--skills-layer)
5. [Phase 4 — Interface Layer](#5-phase-4--interface-layer)
6. [Phase 5 — Integration & Main Loop](#6-phase-5--integration--main-loop)
7. [Phase 6 — Testing & QA](#7-phase-6--testing--qa)
8. [Phase 7 — Phase 2 Features (Post-MVP)](#8-phase-7--phase-2-features-post-mvp)
9. [Dependency Installation Order](#9-dependency-installation-order)
10. [File-by-File Implementation Guide](#10-file-by-file-implementation-guide)
11. [Verification Checklist](#11-verification-checklist)

---

## 1. Project Overview

### Goal
Build **JARVIS-Lite**: a fully offline, privacy-first, voice-controlled desktop assistant that uses Whisper (STT) + spaCy (NLP) + pyttsx3 (TTS) to execute file operations, app control, and system commands via natural language.

### MVP Scope (Phase 1-6)
- Voice input (push-to-talk via SPACE key)
- Whisper STT → spaCy/rule-based NLP → skill execution → pyttsx3 TTS
- Core skills: file ops, app control, volume, screenshot, lock screen
- Conversation context & clarification flows
- Terminal UI with ANSI colors and animations

### Non-MVP (Phase 7+)
- Wake word detection (Porcupine)
- System tray interface (pystray)
- Web dashboard (Flask)
- Piper TTS upgrade
- Plugin hot-reload

---

## 2. Phase 1 — Foundation & Project Scaffold

### 2.1 Directory Structure

Create the full directory tree exactly as specified in PRD §4.4:

```
jarvis/
├── .github/
│   └── workflows/
│       └── tests.yml
├── config/
│   ├── settings.json
│   └── macros.json
├── core/
│   ├── __init__.py
│   ├── audio.py
│   ├── stt.py
│   ├── nlp.py
│   ├── tts.py
│   ├── context.py
│   ├── executor.py
│   ├── config_manager.py
│   ├── model_manager.py
│   └── first_run_wizard.py
├── skills/
│   ├── __init__.py
│   ├── base.py
│   ├── manager.py
│   ├── installer.py
│   ├── third_party/
│   └── core/
│       ├── __init__.py
│       ├── file_operations.py
│       ├── app_control.py
│       ├── system_control.py
│       ├── process_management.py
│       └── macro_skill.py
├── interface/
│   ├── __init__.py
│   ├── cli.py
│   └── ui.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── security.py
│   └── helpers.py
├── models/
│   ├── __init__.py            ← Root-level shared data models
│   └── .gitkeep
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── setup.py
└── main.py
```

### 2.2 Configuration Files

#### `config/settings.json`
*(Note: Consolidating all config into a single source of truth as specified by Backend Schema)*

```json
{
  "pipeline": {
    "stt": {
      "engine": "whisper",
      "model": "base",
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
    "wake_word_enabled": false,
    "save_history": true,
    "verbose_logging": false,
    "push_to_talk_key": "space"
  },
  "skills": {
    "file_operations": {
      "enabled": true,
      "allowed_directories": [
        "~/Documents",
        "~/Desktop",
        "~/Downloads",
        "~/Projects"
      ]
    },
    "app_control": {
      "enabled": true,
      "app_map": {
        "chrome": {"win": "chrome", "mac": "Google Chrome", "linux": "google-chrome"},
        "firefox": {"win": "firefox", "mac": "Firefox", "linux": "firefox"},
        "vscode": {"win": "code", "mac": "Visual Studio Code", "linux": "code"},
        "terminal": {"win": "cmd", "mac": "Terminal", "linux": "gnome-terminal"},
        "notepad": {"win": "notepad", "mac": "TextEdit", "linux": "gedit"},
        "explorer": {"win": "explorer", "mac": "Finder", "linux": "nautilus"}
      }
    },
    "system_control": {
      "enabled": true,
      "screenshot_dir": "~/Desktop"
    },
    "process_management": {
      "enabled": true
    }
  },
  "hotkeys": {
    "push_to_talk": "space",
    "cancel": "escape",
    "help": "f1",
    "exit": "ctrl+q"
  }
}
```
> **Windows Note:** To capture global hotkeys reliably even when another application has focus, the system MUST use `pywin32` (`SetWindowsHookEx`) rather than the `keyboard` library which requires Administrator privileges.

#### `config/macros.json`
```json
{
  "morning routine": [
    {"intent": "open_app", "entity": "chrome"},
    {"intent": "open_file", "entity": "todo.txt"},
    {"intent": "system_info"}
  ]
}
```

### 2.3 Setup Scripts

#### `scripts/download_models.py`
```python
import os
import whisper
import spacy

def main():
    print("Downloading Whisper base model (~74MB)...")
    whisper.load_model("base")
    print("Downloading spaCy en_core_web_sm model (~40MB)...")
    os.system("python -m spacy download en_core_web_sm")
    print("Models downloaded successfully.")

if __name__ == "__main__":
    main()
```

### 2.3 Requirements Files

#### `requirements.txt`
```
# Audio
sounddevice==0.4.6
numpy==1.26.4

# STT
openai-whisper==20231117

# NLP
spacy==3.7.4
rapidfuzz==3.6.1

# TTS
pyttsx3==2.90

# System
psutil==5.9.8
pyautogui==0.9.54
keyboard==0.13.5

# Utils
colorama==0.4.6
python-dotenv==1.0.0
```

#### `requirements-dev.txt`
```
pytest==7.4.4
pytest-benchmark==4.0.0
pytest-mock==3.12.0
black==23.12.1
flake8==7.0.0
mypy==1.8.0
```

### 2.4 `.gitignore`
```
__pycache__/
*.pyc
*.pyo
.env
models/vosk/
models/whisper/
models/piper/
*.log
logs/
.DS_Store
venv/
.venv/
*.egg-info/
dist/
build/
```

---

## 3. Phase 2 — Core Engine Modules

### 3.1 `models.py` — Shared Data Models

**Implement exactly as specified in Backend Schema §2.1.**

Key classes to implement (in order):
1. `State` (Enum) — 10 system states: INITIALIZING → SHUTTING_DOWN
2. `AudioFormat` (Enum) — PCM_16BIT, FLOAT32
3. `IntentType` (Enum) — 13 intent types
4. `ErrorType` (Enum) — 8 error categories
5. `AudioConfig` (dataclass) — sample_rate=16000, channels=1
6. `AudioData` (dataclass) — audio buffer with metadata
7. `Intent` (dataclass) — type + confidence + parameters + raw_text
8. `IntentParseResult` (dataclass) — intent or clarification request
9. `ExecutionResult` (dataclass) — success + message + error_type
10. `ConversationTurn` (dataclass) — role + content + timestamp
11. `ConversationContext` (dataclass) — history (max 50) + clarification state
12. `SkillMetadata` (dataclass) — name, version, description
13. `SystemConfig` (dataclass) — full config with security settings
14. `JarvisError` (dataclass) — typed error with suggestion

**Critical rules:**
- All dataclasses use `field(default_factory=...)` for mutable defaults
- `ConversationContext.add_turn()` auto-prunes to last 50 turns
- `SystemConfig.from_dict()` and `.to_dict()` must be inverse operations

---

### 3.2 `utils/logger.py` — Structured Logging

```python
"""
Structured logging for JARVIS-Lite.
Provides colored console output and optional JSON file logging.
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

class JarvisLogger:
    """Centralized logger with structured output"""
    
    _instance: Optional['JarvisLogger'] = None
    
    def __init__(self, name: str = "jarvis", verbose: bool = False, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        
        # Console handler with color
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)
    
    def info(self, msg: str, **kwargs): ...
    def debug(self, msg: str, **kwargs): ...
    def warning(self, msg: str, **kwargs): ...
    def error(self, msg: str, **kwargs): ...
```

**Implementation notes:**
- `ColoredFormatter` uses ANSI codes matching `Colors` class in `ui.py`
- `JSONFormatter` outputs `{"timestamp": ..., "level": ..., "message": ...}` for file logging
- Singleton pattern via `JarvisLogger._instance`

---

### 3.3 `utils/security.py` — Input Validation

```python
"""
Security validation for commands before execution.
Prevents directory traversal, dangerous commands, and prompt injection.
"""

import re
from pathlib import Path
from typing import Optional, List

DANGEROUS_PATTERNS = [
    r'\.\.',           # Directory traversal
    r'rm\s+-rf',       # Recursive delete
    r'del\s+/[sf]',    # Windows force delete
    r'format\s+[a-z]:', # Disk format
    r'mkfs\.',         # Linux format
    r'eval\(',         # Code execution
    r'exec\(',         # Code execution
    r'__import__',     # Dynamic import
    r'sudo\s+',        # Privilege escalation
]

def validate_file_path(path: str, allowed_dirs: List[str]) -> Optional[str]:
    """
    Validate file path is within allowed directories.
    
    Args:
        path: File path to validate
        allowed_dirs: List of allowed base directories
        
    Returns:
        Resolved path string if valid, None if blocked
    """
    ...

def sanitize_command_text(text: str) -> str:
    """
    Sanitize command text to prevent injection.
    Returns cleaned text or raises SecurityError.
    """
    ...

def is_dangerous_command(text: str) -> bool:
    """Check if command matches dangerous patterns."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in DANGEROUS_PATTERNS)
```

---

### 3.4 `core/audio.py` — Audio Capture

**Implement `AudioInterface` ABC + `SoundDeviceAudio` exactly as in Backend Schema §3.1.**

**Additional implementation details:**

```python
class SoundDeviceAudio(AudioInterface):
    
    def get_waveform_visualization(self, audio_chunk: np.ndarray) -> str:
        """
        Return ASCII waveform for UI display during recording.
        Maps audio amplitude to block characters: ▁▂▃▄▅▆▇█
        """
        levels = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        # Normalize amplitude to 0-7 range
        rms = np.sqrt(np.mean(audio_chunk**2))
        level_idx = min(7, int(rms * 100))
        return levels[level_idx] * 16
    
    def detect_silence(self, audio_chunk: np.ndarray, threshold: float = 0.01) -> bool:
        """Return True if audio chunk is silent (below threshold RMS)."""
        rms = np.sqrt(np.mean(audio_chunk**2))
        return rms < threshold
```

**State machine hook:** `start_recording()` must be called from IDLE→LISTENING transition, `stop_recording()` from LISTENING→TRANSCRIBING.

**Error handling:**
- No microphone → raise `AudioError` with message "No microphone found. Check audio settings."
- Device disconnect during recording → stop gracefully, return partial audio

---

### 3.5 `core/stt.py` — Speech-to-Text

**Implement `STTInterface` ABC + `WhisperSTT` + `VoskSTT` as in Backend Schema §3.2.**

**Loading strategy:**
```python
class WhisperSTT(STTInterface):
    
    def initialize(self, model: str = "base") -> bool:
        """
        Load Whisper model. Shows progress to caller via callback.
        Model is cached after first load (~74MB download on first run).
        """
        import whisper
        self.model = whisper.load_model(model)
        return True
    
    def transcribe(self, audio: AudioData) -> Optional[str]:
        """
        Transcribe audio. Returns None if text is empty or transcription fails.
        Sets self.last_confidence = 0.9 (Whisper doesn't provide per-utterance confidence).
        """
        audio_array = audio.data.astype('float32')
        result = self.model.transcribe(
            audio_array,
            language='en',
            fp16=False,
            verbose=False
        )
        text = result['text'].strip()
        return text if text else None
```

**Fallback logic (in `main.py` / orchestrator):**
```
Try WhisperSTT.transcribe() → success → continue
If exception or returns None → Try VoskSTT.transcribe() → use result
If both fail → transition to ERROR state
```

> **Performance Targets (Hardware Dependent):**
> Inference time varies wildly based on hardware. The system is designed with tiered expectations (as per PRD §6.1):
> - **Tier 1 (GPU/Apple Silicon):** < 1.0s inference
> - **Tier 2 (Modern CPU):** 1.0s - 3.0s inference
> - **Tier 3 (Older CPU):** > 3.0s inference (display "Processing speech..." explicitly to manage expectations)

---

### 3.6 `core/nlp.py` — Intent Parsing

**Phase 1 (MVP): Rule-based NLP**
**Implement `NLPInterface` ABC + `RuleBasedNLP` as the Phase 1 MVP.**

**Complete intent pattern set (Phase 1)**:

```python
self.intent_patterns = {
    IntentType.OPEN_FILE: [
        r'\b(open|show|display|view)\b.*(file|document|pdf|doc|txt)',
        r'\bopen\b.*\.\w{2,4}$',
    ],
    IntentType.OPEN_APP: [
        r'\b(open|launch|start|run)\b.*(chrome|firefox|vscode|code|terminal|notepad|explorer|browser|app)',
    ],
    IntentType.CLOSE_APP: [
        r'\b(close|quit|exit|kill|terminate)\b.*(chrome|firefox|vscode|terminal|\w+)',
    ],
    IntentType.SEARCH_FILES: [
        r'\b(find|search|locate|look for|where is)\b',
    ],
    IntentType.CREATE_FILE: [
        r'\b(create|make|new)\b.*(file|document|note|text)',
    ],
    IntentType.DELETE_FILE: [
        r'\b(delete|remove|trash)\b.*(file|document)',
    ],
    IntentType.VOLUME_CONTROL: [
        r'\bvolume\b.*(up|down|increase|decrease|higher|lower|mute)',
        r'\b(increase|decrease|raise|lower)\b.*volume',
    ],
    IntentType.SCREENSHOT: [
        r'\b(take|capture|grab)\b.*(screenshot|screen|screen shot)',
        r'\bscreenshot\b',
    ],
    IntentType.LOCK_SCREEN: [
        r'\block\b.*(screen|computer|system|workstation)',
        r'\block screen\b',
    ],
    IntentType.SYSTEM_INFO: [
        r'\b(what is|show|how much)\b.*(cpu|memory|ram|disk|battery)',
        r'\bsystem (info|stats|status)\b',
    ],
    IntentType.HELP: [
        r'\b(help|commands|what can you do|show commands)\b',
    ],
    IntentType.EXIT: [
        r'\b(exit|quit|goodbye|bye|stop|shutdown jarvis)\b',
    ],
    IntentType.UNDO: [
        r'\b(undo|cancel that|revert|nevermind|go back)\b',
    ],
    IntentType.REPEAT: [
        r'\b(repeat|say that again|what did you say)\b',
    ],
    IntentType.MACRO: [
        r'\b(run|execute)\b.*\b(routine|macro)\b',
        r'\b(morning routine|evening routine)\b',
    ],
}
```

**Parameter extractor** — `_extract_parameters()` must handle:
- `OPEN_FILE`: Extract filename after "open", strip common words ("the", "my", "a")
- `OPEN_APP`: Match against known app aliases (chrome→chrome, browser→chrome, code→vscode)
- `CLOSE_APP`: Same as OPEN_APP extraction
- `SEARCH_FILES`: Everything after the search verb
- `VOLUME_CONTROL`: "up"/"down" direction
- `CREATE_FILE`: Filename after "create/make/new [a/the] file called/named"

**Clarification resolution** (Backend Schema §3.3 `resolve_clarification`):
- Try digit input (1, 2, 3) → index into `context.clarification_options`
- Try ordinal words ("first", "second", "third") → same mapping
- Try rapidfuzz matching (threshold 70%) against option list
- If all fail → return None → speak "I couldn't match that. Try saying the number."

**Confidence Floor & "Did you mean?" (F2.x):**
- If max confidence is between `0.4` and `0.75` (configurable threshold):
  Set `requires_clarification = True`
  `clarification_message` = "Did you mean [matched_intent]?"
- If confidence < `0.4`:
  Return `ErrorType.NOT_UNDERSTOOD`

**State Machine Fix (PARSING):**
- `parse_intent(text, context)` MUST check `if context.awaiting_clarification:` BEFORE attempting a fresh Regex parse. If true, route text to `resolve_clarification` first.

**Phase 2 (Post-MVP): LLM-native NLP**
In Phase 2, `RuleBasedNLP` will be swapped with `LLMNativeNLP`, utilizing a local quantized LLM for complex multi-intent extraction and contextual resolution, while sharing the same `IntentType` Enum interface to ensure downward compatibility.

---

### 3.7 `core/tts.py` — Text-to-Speech

**Implement `TTSInterface` ABC + `Pyttsx3TTS` as in Backend Schema §3.4.**

**Thread safety & Barge-in note:** pyttsx3's `runAndWait()` is blocking. To support TTS interruption (Barge-in), run the engine in a dedicated daemon thread using `engine.startLoop(False)` + `engine.iterate()`. A global `tts_interrupt_flag` (threading.Event) should be checked on every tick; if set, immediately stop the engine and flush the audio queue.

**Voice selection:**
```python
def _select_voice(self):
    """Select best available voice (prefer male/neutral)"""
    voices = self.engine.getProperty('voices')
    # Windows: prefer SAPI5 David (en-US)
    # macOS: prefer Alex or Daniel  
    # Linux: espeak default
    for voice in voices:
        if 'david' in voice.name.lower() or 'alex' in voice.name.lower():
            self.engine.setProperty('voice', voice.id)
            return
    # Fall back to first available
    if voices:
        self.engine.setProperty('voice', voices[0].id)
```

---

### 3.8 `core/context.py` — Conversation State

**Implement `ConversationContext` as standalone module, matching `models.py` dataclass exactly.**

**Additional methods beyond schema:**

```python
def get_context_summary(self) -> str:
    """
    Return brief context for NLP disambiguation.
    Used when parsing ambiguous references like "that file" or "the previous one".
    """
    if not self.history:
        return ""
    last_turn = self.history[-1]
    return f"Last: {last_turn.role}={last_turn.content[:50]}"

def save_to_file(self, filepath: str):
    """Persist context to JSON file (call on shutdown if save_history=True)"""
    import json
    with open(filepath, 'w') as f:
        json.dump(self.to_dict(), f, indent=2, default=str)

@classmethod
def load_from_file(cls, filepath: str) -> 'ConversationContext':
    """Restore context from previous session"""
    import json
    with open(filepath) as f:
        data = json.load(f)
    ctx = cls()
    # Restore history (simplified, skip intent/result restoration)
    for turn_data in data.get('history', []):
        ctx.history.append(ConversationTurn(
            role=turn_data['role'],
            content=turn_data['content']
        ))
    
    # Advanced Feature: Load Core Beliefs
    try:
        import sqlite3
        conn = sqlite3.connect('core_memory.sqlite')
        cursor = conn.cursor()
        cursor.execute("SELECT belief FROM core_beliefs")
        ctx.core_beliefs = [row[0] for row in cursor.fetchall()]
        conn.close()
    except Exception:
        pass
        
    return ctx
```

---

### 3.9 `core/executor.py` — Command Execution

**Implement `ExecutorInterface` ABC + `SkillBasedExecutor` as in Backend Schema §3.5.**

**Intent → Skill routing table:**
```python
INTENT_SKILL_MAP = {
    IntentType.OPEN_FILE:       "file_operations",
    IntentType.SEARCH_FILES:    "file_operations",
    IntentType.CREATE_FILE:     "file_operations",
    IntentType.DELETE_FILE:     "file_operations",
    IntentType.OPEN_APP:        "app_control",
    IntentType.CLOSE_APP:       "app_control",
    IntentType.VOLUME_CONTROL:  "system_control",
    IntentType.SCREENSHOT:      "system_control",
    IntentType.LOCK_SCREEN:     "system_control",
    IntentType.SYSTEM_INFO:     "process_management",
    IntentType.HELP:            None,  # Handled inline
    IntentType.EXIT:            None,  # Handled inline
    IntentType.UNDO:            None,  # Handled inline by Executor
    IntentType.REPEAT:          None,  # Handled inline by Executor
    IntentType.MACRO:           "macro_skill",
}
```

**Execution wrapper:**
```python
def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
    # 1. Security check
    if not validate_safe_execution(intent):
        return ExecutionResult(success=False, message="Command blocked for safety",
                               error_type=ErrorType.PERMISSION_DENIED)
    
    # 2. Route to skill
    # 3. Execute with 5-second timeout
    # 4. Context variable writes (MUST happen after successful execution)
    #    - If search_files -> context.set_variable('last_search_results', result)
    #    - If open_file/app -> context.set_variable('last_opened_file/app', intent.entity)
    #    - Always set context.last_intent = intent (for undo/repeat)
    # 5. Return result
```

---

### 3.10 `core/config_manager.py` — Configuration

```python
"""
Loads and validates configuration from config/settings.json and config/macros.json.
Supports live reload (watches for file changes).
"""

import json
from pathlib import Path
from models import SystemConfig

class ConfigManager:
    
    CONFIG_FILE = Path("config/settings.json")
    MACRO_FILE = Path("config/macros.json")
    
    def __init__(self):
        self.config = {}
        self.macros = {}
    
    def load_all(self) -> SystemConfig:
        """Load settings.json and merge into SystemConfig"""
        ...
    
    def get(self, key: str, default=None):
        """Dot-notation config access: get('pipeline.stt.engine')"""
        ...
    
    def reload(self):
        """Re-read config files from disk"""
        ...
```

---

### 3.11 `core/first_run_wizard.py` — First-Run Setup (F6)

```python
"""
Guided CLI wizard that runs if config/settings.json is missing.
Walks user through basic configuration.
"""
def run_setup_wizard():
    print("Welcome to JARVIS-Lite. Let's set up your environment.")
    # 1. Ask for preferred voice/language
    # 2. Ask for trusted directories (default ~/Desktop, ~/Documents)
    # 3. Ask for push-to-talk key (default Space)
    # 4. Generate config/settings.json
    # 5. Check dependencies (download models if needed)
    print("Setup complete. You're ready to go.")
```

---

## 4. Phase 3 — Skills Layer

### 4.1 `skills/base.py` — Skill Base Class

```python
"""
Base class for all JARVIS skills.
Every skill inherits from BaseSkill and implements execute().
"""

from abc import ABC, abstractmethod
from models import Intent, ExecutionResult, ConversationContext, SkillMetadata

class BaseSkill(ABC):
    """Abstract base for all JARVIS skills"""
    
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = ...  # Inject logger
    
    @abstractmethod
    def initialize(self) -> bool:
        """Called once when skill is loaded. Return True if ready."""
        pass
    
    @abstractmethod
    def get_handled_intents(self) -> list:
        """Return list of IntentType values this skill handles."""
        pass
    
    @abstractmethod
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Execute the intent. Return ExecutionResult."""
        pass
    
    def shutdown(self):
        """Called on system shutdown. Override for cleanup."""
        pass
    
    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            functions=self.get_handled_intents()
        )
```

---

### 4.2 `skills/manager.py` — Skill Registry

```python
"""
Discovers, loads, and manages all skills.
Auto-discovers skills from skills/core/ and skills/third_party/ on startup.
Parses `manifest.json` for capabilities and dependency isolation.
"""

from pathlib import Path
from typing import Dict, Optional
import subprocess
from models import IntentType, Intent, ExecutionResult, ConversationContext, SkillManifest
from skills.base import BaseSkill

class SkillManager:
    
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.intent_map: Dict[IntentType, str] = {}
    
    def load_core_skills(self, config: dict) -> bool:
        """Load all skills from skills/core/ directory"""
        from skills.core.file_operations import FileOperationsSkill
        from skills.core.app_control import AppControlSkill
        from skills.core.system_control import SystemControlSkill
        from skills.core.process_management import ProcessManagementSkill
        
        skill_classes = [
            (FileOperationsSkill, config.get('file_operations', {})),
            (AppControlSkill, config.get('app_control', {})),
            (SystemControlSkill, config.get('system_control', {})),
            (ProcessManagementSkill, config.get('process_management', {})),
        ]
        
        for SkillClass, skill_config in skill_classes:
            skill = SkillClass(skill_config)
            if skill.initialize():
                self.skills[skill.name] = skill
                for intent_type in skill.get_handled_intents():
                    self.intent_map[intent_type] = skill.name
        
        return len(self.skills) > 0
    
    def dispatch(self, intent: Intent, context: ConversationContext) -> Optional[ExecutionResult]:
        """Route intent to appropriate skill"""
        skill_name = self.intent_map.get(intent.type)
        if not skill_name:
            return None
        skill = self.skills.get(skill_name)
        if not skill:
            return None
            
        # Security: Enforce Capability Manifests
        from utils.security import validate_capabilities
        if not validate_capabilities(skill, intent):
            return ExecutionResult(success=False, message="Permission denied by manifest")
            
        return skill.execute(intent, context)
```

---

### 4.2.1 `skills/installer.py` — Skill Installer (Advanced)

```python
"""
Installs third-party skills from GitHub into isolated virtual environments.
Usage: jarvis --install-skill <github-url>
"""
import os
import subprocess
from pathlib import Path

def install_skill(repo_url: str):
    # 1. Clone into skills/third_party/<skill_name>
    # 2. Extract capabilities from manifest.json and prompt user for approval
    # 3. Create isolated python virtual environment (python -m venv venv)
    # 4. pip install -r requirements.txt within that venv
    pass
```

---

### 4.3 `skills/core/file_operations.py` — File Skill

**Handles:** OPEN_FILE, SEARCH_FILES, CREATE_FILE, DELETE_FILE (with confirmation)

```python
class FileOperationsSkill(BaseSkill):
    name = "file_operations"
    description = "Open, search, create, and delete files"
    
    def get_handled_intents(self):
        return [IntentType.OPEN_FILE, IntentType.SEARCH_FILES,
                IntentType.CREATE_FILE, IntentType.DELETE_FILE]
    
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        handlers = {
            IntentType.OPEN_FILE:    self._open_file,
            IntentType.SEARCH_FILES: self._search_files,
            IntentType.CREATE_FILE:  self._create_file,
            IntentType.DELETE_FILE:  self._delete_file,
        }
        handler = handlers.get(intent.type)
        return handler(intent, context) if handler else ExecutionResult(
            success=False, message="Unknown file operation"
        )
    
    def _open_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        1. Extract filename from intent.parameters['filename']
        2. Search in allowed_directories using pathlib.Path.rglob()
        3. If 0 matches → ExecutionResult(success=False, message="File not found: {name}")
        4. If 1 match → open with os.startfile() (Win) or subprocess.run(['open']) (Mac)
        5. If multiple matches → return ExecutionResult with requires_clarification=True
           and set context.set_clarification(intent, [list of matches])
        """
        ...
    
    def _search_files(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Search by query string using rglob("*{query}*") in allowed dirs.
        Return formatted list of up to 10 matches.
        """
        ...
    
    def _create_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Create empty text file on Desktop (or specified location)."""
        ...
    
    def _delete_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        ALWAYS require confirmation. Set context variable 'pending_delete'.
        Never auto-delete without explicit "yes" from user.
        """
        ...
```

**Clarification flow for multi-match files:**
```python
# In _open_file, when multiple matches found:
context.set_clarification(intent, [str(p) for p in matches[:5]])
return ExecutionResult(
    success=True,
    message=f"Found {len(matches)} files. Which one?",
    data={"options": [str(p) for p in matches[:5]], "requires_clarification": True}
)
```

---

### 4.4 `skills/core/app_control.py` — App Control Skill

**Handles:** OPEN_APP, CLOSE_APP

```python
class AppControlSkill(BaseSkill):
    name = "app_control"
    
    # Load app_map from config/skills.json
    def _get_app_command(self, app_name: str) -> Optional[str]:
        """
        Look up platform-specific command for app name.
        Supports aliases: "browser" → "chrome", "editor" → "vscode"
        """
        import sys
        platform = 'win' if sys.platform == 'win32' else 'mac' if sys.platform == 'darwin' else 'linux'
        app_map = self.config.get('app_map', {})
        
        # Normalize aliases
        aliases = {
            'browser': 'chrome', 'web': 'chrome', 'internet': 'chrome',
            'editor': 'vscode', 'code editor': 'vscode',
            'cmd': 'terminal', 'command prompt': 'terminal',
        }
        normalized = aliases.get(app_name.lower(), app_name.lower())
        
        app_entry = app_map.get(normalized)
        return app_entry.get(platform) if app_entry else None
    
    def _open_app(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        1. Get app name from intent.parameters['app_name']
        2. Look up command via _get_app_command()
        3. Launch with subprocess.Popen([command]) (non-blocking)
        4. Return "Launching {app_name}"
        """
        ...
    
    def _close_app(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        1. Find process by name using psutil.process_iter()
        2. Terminate with proc.terminate()
        3. Wait up to 3 seconds for graceful exit
        4. Force kill if still running: proc.kill()
        """
        ...
```

---

### 4.5 `skills/core/system_control.py` — System Skill

**Handles:** VOLUME_CONTROL, SCREENSHOT, LOCK_SCREEN

```python
class SystemControlSkill(BaseSkill):
    name = "system_control"
    
    def _adjust_volume(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Windows: Use pycaw or ctypes WinMM
        macOS: subprocess osascript -e 'set volume output volume X'
        Linux: subprocess amixer set Master X%
        Direction from intent.parameters['action'] ('up' or 'down')
        Step: 10% per command
        """
        ...
    
    def _take_screenshot(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Use pyautogui.screenshot() → save to ~/Desktop/screenshot_{timestamp}.png
        Return "Screenshot saved to Desktop"
        """
        import pyautogui
        from datetime import datetime
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = Path.home() / "Desktop" / filename
        pyautogui.screenshot(str(save_path))
        return ExecutionResult(success=True, message=f"Screenshot saved: {filename}")
    
    def _lock_screen(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Windows: subprocess.run(['rundll32', 'user32.dll,LockWorkStation'])
        macOS: subprocess.run(['pmset', 'displaysleepnow'])
        Linux: subprocess.run(['loginctl', 'lock-session'])
        """
        ...
```

---

### 4.6 `skills/core/process_management.py` — Process Skill

**Handles:** SYSTEM_INFO (list processes, CPU/RAM stats)

```python
class ProcessManagementSkill(BaseSkill):
    name = "process_management"
    
    def _get_system_info(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Use psutil to get: cpu_percent, virtual_memory().percent, disk_usage('/').percent
        Format as readable string: "CPU: 23%, RAM: 45% (7.2GB used), Disk: 67%"
        """
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        msg = f"CPU: {cpu}%, RAM: {mem.percent}% ({mem.used // 1024**3}GB used), Disk: {disk.percent}%"
        return ExecutionResult(success=True, message=msg)
```

---

### 4.7 `skills/core/macro_skill.py` — Macro Skill (F5)

**Handles:** MACRO

```python
class MacroSkill(BaseSkill):
    name = "macro_skill"
    
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        1. Look up macro by intent.parameters['macro_name'] in config/macros.json
        2. If not found -> Error: "Macro not found"
        3. For each step in macro:
           a. Construct sub-intent
           b. Recursively call execute_intent_list() (or main executor)
        """
        ...
```

---

## 5. Phase 4 — Interface Layer

### 5.1 `interface/ui.py` — Terminal UI

**Implement exactly from Frontend Guidelines §2.1** — copy `Colors`, `Icons`, `Box`, `TerminalUI` classes verbatim.

**Critical additions:**

```python
class TerminalUI:
    
    def show_progress(self, message: str, percent: int):
        """Show loading progress bar during initialization"""
        filled = int(percent / 5)  # 20 slots for 0-100%
        bar = '█' * filled + '░' * (20 - filled)
        print(f"\r{Colors.PRIMARY}[{bar}]{Colors.RESET} {percent}% {message}", 
              end='', flush=True)
    
    def show_state(self, state: 'State'):
        """Update display for current state machine state"""
        state_displays = {
            'IDLE':        self.show_idle_prompt,
            'LISTENING':   self.show_listening,
            'TRANSCRIBING': lambda: self.show_processing("Processing speech"),
            'PARSING':     lambda: self.show_processing("Understanding command"),
            'EXECUTING':   lambda: self.show_executing("Running command"),
            'ERROR':       lambda: None,  # Error shown separately
        }
        display_fn = state_displays.get(state.value)
        if display_fn:
            display_fn()
```

**Thread safety:** All `print()` calls in animations run in daemon threads. Use `self._animation_active` flag to stop cleanly.

---

### 5.2 `interface/cli.py` — Command Line Interface

```python
"""
CLI entry point and keyboard event loop.
Handles push-to-talk (SPACE key) and text input mode.
"""

import threading
import keyboard
from interface.ui import TerminalUI
from models import State

class CLI:
    """Command-line interface for JARVIS-Lite"""
    
    def __init__(self, jarvis_engine):
        self.engine = jarvis_engine
        self.ui = TerminalUI()
        self.running = True
        self.ptt_key = 'space'
    
    def run(self):
        """Main event loop"""
        self.ui.show_startup()
        self.engine.initialize(progress_callback=self.ui.show_loading_step)
        self.ui.show_startup_complete()
        
        while self.running:
            self.ui.show_idle_prompt()
            
            # Wait for push-to-talk or text input
            text_input = self._wait_for_input()
            
            if text_input is None:
                # Push-to-talk: record audio
                self._handle_voice_input()
            elif text_input.lower() in ('exit', 'quit', 'bye'):
                self._shutdown()
            elif text_input.lower() == 'help':
                self.ui.show_help()
                input()  # Wait for any key
            else:
                # Text command: skip STT
                self.engine.process_text(text_input)
    
    def _wait_for_input(self) -> Optional[str]:
        """
        Wait for SPACE (PTT) or Enter (text mode).
        Returns text if typed, None if SPACE was held.
        
        # Barge-in: If SPACE is pressed and engine state is RESPONDING:
        # tts_interrupt_flag.set()
        """
        # Use pywin32 global hook or keyboard.read_event() in a thread-safe manner
        ...
    
    def _handle_voice_input(self):
        """
        1. Show listening animation
        2. Record while SPACE is held
        3. Stop on SPACE release or silence or 10s timeout
        4. Pass audio to engine
        """
        ...
```

---

## 6. Phase 5 — Integration & Main Loop

### 6.1 Main Engine Class

**Create `jarvis_engine.py` at project root:**

```python
"""
JARVIS Engine — Orchestrates all components.
Implements the state machine from Appflow.md §2.
"""

from models import State, ConversationContext, SystemConfig
from core.audio import SoundDeviceAudio
from core.stt import WhisperSTT, VoskSTT
from core.nlp import RuleBasedNLP
from core.tts import Pyttsx3TTS
from core.executor import SkillBasedExecutor
from core.config_manager import ConfigManager
from core.model_manager import ModelManager  # VRAM Orchestrator
from skills.manager import SkillManager
from utils.logger import JarvisLogger
from utils.security import is_dangerous_command

class JarvisEngine:
    """Main orchestrator for JARVIS-Lite"""
    
    def __init__(self):
        self.state = State.INITIALIZING
        self.context = ConversationContext()
        self.config = None
        self.logger = JarvisLogger()
        
        # Components (initialized in initialize())
        self.audio = SoundDeviceAudio()
        self.stt = WhisperSTT()
        self.stt_fallback = VoskSTT()
        self.nlp = RuleBasedNLP()
        self.tts = Pyttsx3TTS()
        self.skill_manager = SkillManager()
        self.model_manager = ModelManager(self.stt, self.nlp)
    
    def initialize(self, progress_callback=None) -> bool:
        """
        Follows INITIALIZING state from Appflow §2.2.
        Calls progress_callback(message, percent) at each step.
        
        Steps:
        1. Load config (10%)
        2. Load spaCy NLP (30%)
        3. Initialize audio devices (50%)
        4. Load Whisper model (80%)
        5. Initialize TTS (90%)
        6. Load skills (100%)
        
        Returns True if all critical components loaded.
        Critical: audio, stt, nlp, tts
        Non-critical: skill failures (warn but continue)
        """
        ...
    
    def process_audio(self, audio_data) -> str:
        """TRANSCRIBING state: audio → text"""
        self.model_manager.prepare_for_stt()  # Evicts LLM from VRAM
        text = self.stt.transcribe(audio_data)
        if text is None:
            text = self.stt_fallback.transcribe(audio_data)
            
        if text:
            # F1.7 — STT Confirmation Display
            print(f"  I heard: '{text}'  (ESC to cancel)")
            import time, keyboard
            start = time.time()
            while time.time() - start < 1.5:
                if keyboard.is_pressed('escape'):
                    return None  # Cancelled
                time.sleep(0.05)
                
        return text
    
    def process_text(self, text: str) -> str:
        """PARSING + EXECUTING + RESPONDING: text → response"""
        # Security check
        if is_dangerous_command(text):
            response = "I can't do that — it looks like a dangerous command."
            self.tts.speak(response)
            return response
        
        
        # Parse intent
        self.model_manager.prepare_for_nlp()  # Evicts STT, loads LLM
        parse_result = self.nlp.parse_intent(text, self.context)
        
        # Handle clarification
        if parse_result.requires_clarification:
            self.context.set_clarification(parse_result.intent, 
                                           parse_result.clarification_options)
            self.tts.speak(parse_result.clarification_message)
            return parse_result.clarification_message
        
        # Execute
        result = self.skill_manager.dispatch(parse_result.intent, self.context)
        
        # Handle HELP and EXIT inline
        if parse_result.intent.type == IntentType.HELP:
            return self._handle_help()
        if parse_result.intent.type == IntentType.EXIT:
            return self._handle_exit()
        
        # TTS response
        response = result.message if result else "I don't know how to do that yet."
        self.context.add_turn('user', text)
        self.context.add_turn('assistant', response)
        self.tts.speak(response)
        
        return response
```

---

### 6.2 `main.py` — Entry Point

```python
"""
JARVIS-Lite — Main entry point
Usage: python main.py [--cli] [--verbose] [--no-voice] [--test-stt] [--test-tts TEXT]
"""

import argparse
import sys
from jarvis_engine import JarvisEngine
from interface.cli import CLI

def parse_args():
    parser = argparse.ArgumentParser(description='JARVIS-Lite Voice Assistant')
    parser.add_argument('--cli',        action='store_true', help='Text-only mode')
    parser.add_argument('--verbose',    action='store_true', help='Verbose logging')
    parser.add_argument('--no-voice',   action='store_true', help='Disable TTS output')
    parser.add_argument('--test-stt',   action='store_true', help='Test STT pipeline')
    parser.add_argument('--test-tts',   type=str,            help='Test TTS with text')
    parser.add_argument('--config',     type=str,            help='Custom config path')
    return parser.parse_args()

def main():
    args = parse_args()
    
    args = parser.parse_args()
    
    if args.diagnose:
        print("Running system diagnostics...")
        # Check audio devices, model paths, permissions
        sys.exit(0)
        
    config_manager = ConfigManager()
    if not config_manager.CONFIG_FILE.exists():
        run_setup_wizard()
        
    engine = JarvisEngine()
    cli = CLI(engine)
    
    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        engine.shutdown()

if __name__ == "__main__":
    main()
---

## 7. Phase 6 — Testing & QA

### 7.1 Unit Tests

**`tests/test_nlp.py`** — Test each intent pattern:
```python
import pytest
from core.nlp import RuleBasedNLP
from models import ConversationContext, IntentType

@pytest.fixture
def nlp():
    n = RuleBasedNLP()
    n.initialize()
    return n

@pytest.fixture
def ctx():
    return ConversationContext()

class TestIntentParsing:
    def test_open_chrome(self, nlp, ctx):
        result = nlp.parse_intent("open chrome", ctx)
        assert result.intent.type == IntentType.OPEN_APP
        assert result.intent.parameters.get('app_name') == 'chrome'
    
    def test_open_chrome_variations(self, nlp, ctx):
        phrases = ["launch chrome", "start chrome", "open the browser"]
        for phrase in phrases:
            result = nlp.parse_intent(phrase, ctx)
            assert result.intent.type == IntentType.OPEN_APP, f"Failed for: {phrase}"
    
    def test_search_files(self, nlp, ctx):
        result = nlp.parse_intent("find my resume", ctx)
        assert result.intent.type == IntentType.SEARCH_FILES
        assert 'resume' in result.intent.parameters.get('query', '')
    
    def test_volume_up(self, nlp, ctx):
        result = nlp.parse_intent("volume up", ctx)
        assert result.intent.type == IntentType.VOLUME_CONTROL
        assert result.intent.parameters.get('action') == 'up'
    
    def test_screenshot(self, nlp, ctx):
        result = nlp.parse_intent("take a screenshot", ctx)
        assert result.intent.type == IntentType.SCREENSHOT
    
    def test_unknown_intent(self, nlp, ctx):
        result = nlp.parse_intent("blargle froop zorp", ctx)
        assert result.intent.type == IntentType.UNKNOWN
    
    def test_help_intent(self, nlp, ctx):
        result = nlp.parse_intent("help", ctx)
        assert result.intent.type == IntentType.HELP
    
    def test_exit_intent(self, nlp, ctx):
        for phrase in ["exit", "quit", "goodbye", "bye"]:
            result = nlp.parse_intent(phrase, ctx)
            assert result.intent.type == IntentType.EXIT
```

**`tests/test_context.py`** — Test clarification flow:
```python
def test_clarification_set_and_resolve_by_number(ctx):
    from models import Intent, IntentType
    intent = Intent(type=IntentType.OPEN_FILE, confidence=0.9)
    ctx.set_clarification(intent, ["resume.pdf", "resume_2024.pdf", "resume_old.pdf"])
    assert ctx.awaiting_clarification is True
    assert len(ctx.clarification_options) == 3

def test_resolve_clarification_by_fuzzy(ctx, nlp):
    intent = Intent(type=IntentType.OPEN_FILE, confidence=0.9)
    ctx.set_clarification(intent, ["resume.pdf", "resume_2024.pdf"])
    resolved = nlp.resolve_clarification("resume 2024", ctx)
    assert resolved is not None
    assert "resume_2024" in resolved.parameters.get('filename', '')
```

**`tests/test_skills.py`** — Test skill execution:
```python
def test_file_search_returns_results(tmp_path):
    # Create test files
    (tmp_path / "resume.pdf").touch()
    (tmp_path / "resume_old.pdf").touch()
    
    skill = FileOperationsSkill({'allowed_directories': [str(tmp_path)]})
    skill.initialize()
    
    intent = Intent(type=IntentType.SEARCH_FILES, confidence=0.9, 
                    parameters={'query': 'resume'})
    ctx = ConversationContext()
    result = skill.execute(intent, ctx)
    assert result.success
    assert "resume" in result.message.lower()
```

**`tests/test_security.py`** — Test security validator:
```python
def test_blocks_directory_traversal():
    from utils.security import validate_file_path
    assert validate_file_path("../../etc/passwd", ["/home/user"]) is None

def test_blocks_dangerous_commands():
    from utils.security import is_dangerous_command
    assert is_dangerous_command("rm -rf /") is True
    assert is_dangerous_command("open chrome") is False
```

### 7.2 Manual Verification Tests

Run these scenarios after full integration:

| # | Command | Expected Behavior |
|---|---------|-------------------|
| 1 | "open chrome" | Chrome launches, TTS says "Launching Chrome" |
| 2 | "find my resume" | Returns list of matching files |
| 3 | "open my resume" (3 files found) | System asks "Which one? 1. resume.pdf 2. ..." |
| 4 | (after above) "the second one" | Opens second file |
| 5 | "volume up" | Volume increases 10% |
| 6 | "take a screenshot" | Screenshot saved to Desktop |
| 7 | "what is my CPU usage" | Returns "CPU: X%, RAM: Y%" |
| 8 | "help" | Help screen displayed |
| 9 | "blargle froop" | "I didn't understand. Say 'help' for examples." |
| 10 | "exit" | Graceful shutdown |

### 7.3 Performance Benchmarks

Run `python scripts/benchmark.py` targeting:
- STT latency: < 2 seconds for 5-second audio clip
- NLP parsing: < 100ms per intent
- Skill execution (file ops): < 500ms
- TTS first-word latency: < 800ms
- Full loop (voice → response audio): < 7 seconds

---

## 8. Phase 7 — Phase 2 Features (Post-MVP)

### 8.1 Wake Word Detection (F7)
- Library: Porcupine (pvporcupine)
- Integrate into `core/audio.py` as background listener thread
- Toggle via `config/pipeline.json` → `features.wake_word_enabled`

### 8.2 Piper TTS Upgrade (F4)
- Library: piper-tts==1.2.0
- Add `PiperTTS(TTSInterface)` class in `core/tts.py`
- Auto-detect Piper availability; fall back to pyttsx3

### 8.3 System Tray (F9)
- Library: pystray
- Create `interface/tray.py` with icon states (green/blue/red/gray)
- Right-click menu: Enable/Disable, Settings, History, Quit

### 8.4 Web Dashboard (F11)
- Library: Flask 3.x
- Create `interface/web/` with routes for: status, history, skills, settings, logs
- WebSocket for real-time log streaming

### 8.5 LLM Upgrade (F2 — Ollama)
- Replace `RuleBasedNLP` with `OllamaNLP(NLPInterface)` 
- Use function-calling protocol with Llama 3.2 3B
- Keep `RuleBasedNLP` as fallback

---

## 9. Dependency Installation Order

**Follow this order exactly to avoid conflicts:**

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 2. Upgrade pip
pip install --upgrade pip

# 3. Install NumPy first (Whisper dependency)
pip install numpy==1.26.4

# 4. Install audio library
pip install sounddevice==0.4.6

# 5. Install Whisper (downloads PyTorch ~2GB on first install)
pip install openai-whisper==20231117

# 6. Install spaCy + download model
pip install spacy==3.7.4
python -m spacy download en_core_web_sm

# 7. Install NLP utilities
pip install rapidfuzz==3.6.1

# 8. Install TTS
pip install pyttsx3==2.90

# 9. Install system utilities
pip install psutil==5.9.8
pip install pyautogui==0.9.54
pip install keyboard==0.13.5

# 10. Install utilities
pip install colorama==0.4.6 python-dotenv==1.0.0

# 11. Windows-specific for volume control
pip install comtypes  # For pycaw on Windows

# 12. Dev dependencies
pip install pytest==7.4.4 pytest-mock==3.12.0

# 13. Windows: FFmpeg required by Whisper
# Download from https://ffmpeg.org → add to PATH
```

**Known Windows issues:**
- `keyboard` library requires admin rights for global hotkeys → Run as administrator OR use `keyboard.add_hotkey()` which works without admin for most cases
- PyAudio fallback on Windows: `pip install pipwin && pipwin install pyaudio`
- Volume control: use `ctypes` WinMM API or `pycaw` library

---

## 10. File-by-File Implementation Guide

### Implementation Order (strict dependency order)

```
Week 1 — Foundation
─────────────────────────────────────────────────────────────
Day 1: Project scaffold (directories, config files, .gitignore)
Day 1: models.py (all dataclasses and enums)
Day 2: utils/logger.py + utils/security.py + utils/helpers.py
Day 2: core/config_manager.py
Day 3: core/audio.py (SoundDeviceAudio)
Day 3: core/stt.py (WhisperSTT + VoskSTT)

Week 2 — Intelligence
─────────────────────────────────────────────────────────────
Day 4: core/nlp.py (RuleBasedNLP + all patterns)
Day 4: core/tts.py (Pyttsx3TTS)
Day 5: core/context.py (ConversationContext with save/load)
Day 5: core/executor.py (SkillBasedExecutor)

Week 3 — Skills
─────────────────────────────────────────────────────────────
Day 6: skills/base.py + skills/manager.py
Day 6: skills/core/file_operations.py
Day 7: skills/core/app_control.py
Day 7: skills/core/system_control.py + process_management.py

Week 4 — Interface & Integration
─────────────────────────────────────────────────────────────
Day 8: interface/ui.py (TerminalUI — copy from frontend_guidelines.md)
Day 8: interface/cli.py (keyboard event loop)
Day 9: jarvis_engine.py (main orchestrator)
Day 9: main.py (entry point with argparse)
Day 10: Integration testing + bug fixes
Day 10: tests/ (unit tests for all modules)
```

### Key Interfaces Between Modules

```
main.py
  └── JarvisEngine
        ├── ConfigManager    → loads config/*.json
        ├── SoundDeviceAudio → AudioData objects
        ├── WhisperSTT       → str (transcribed text)
        ├── RuleBasedNLP     → IntentParseResult
        ├── SkillManager
        │     ├── FileOperationsSkill    → ExecutionResult
        │     ├── AppControlSkill       → ExecutionResult
        │     ├── SystemControlSkill    → ExecutionResult
        │     └── ProcessManagementSkill → ExecutionResult
        └── Pyttsx3TTS       → audio output
```

---

## 11. Verification Checklist

### Pre-Integration Checks
- [ ] `models.py` — All 14 dataclasses/enums import without errors
- [ ] `utils/security.py` — 5 dangerous patterns blocked, safe patterns pass
- [ ] `core/audio.py` — `list_devices()` returns at least 1 microphone
- [ ] `core/stt.py` — Whisper model loads and transcribes test WAV
- [ ] `core/nlp.py` — All 12 intent types parseable from sample commands
- [ ] `core/tts.py` — `speak("Hello JARVIS")` produces audible output
- [ ] Skills — Each skill's `initialize()` returns True
- [ ] `interface/ui.py` — All UI states display correctly in terminal

### Full System Checks
- [ ] `python main.py --test-tts "Hello"` → Voice output heard
- [ ] `python main.py --cli` → Text mode works for all intents
- [ ] `python main.py` → Full voice loop completes one command
- [ ] Clarification flow: ambiguous file opens → disambiguation → correct file opens
- [ ] Error handling: unknown command → friendly error message + TTS
- [ ] 10-second timeout: no speech → returns to IDLE state
- [ ] ESC key: cancels current operation cleanly
- [ ] `exit` command: graceful shutdown with "Goodbye!"
- [ ] `pytest tests/` → All unit tests pass

### Performance Checks
- [ ] Cold start (python main.py → "Ready"): < 10 seconds
- [ ] STT latency for 3-second audio: < 2 seconds
- [ ] NLP parse time: < 200ms
- [ ] File search (50K files): < 2 seconds
- [ ] TTS response start: < 800ms

---

## Appendix A: State Machine Quick Reference

| State | Trigger In | Trigger Out | Visual |
|-------|-----------|-------------|--------|
| INITIALIZING | App start | All components loaded | Progress bar |
| IDLE | Response done / Error handled | SPACE pressed | `> _` prompt |
| LISTENING | SPACE held | SPACE released / Silence / 10s timeout | Waveform animation |
| TRANSCRIBING | Audio captured | Text produced | Spinner |
| PARSING | Text ready | Intent detected | Spinner |
| CLARIFYING | Multiple file matches | User responds | Numbered list |
| EXECUTING | Intent clear | Skill returns | ⚙ message |
| RESPONDING | Execution done | TTS complete | 🤖 message |
| ERROR | Any failure | Error spoken | ❌ box |
| SHUTTING_DOWN | "exit" / ESC | Process exit | 👋 |

---

## Appendix B: Common Pitfalls & Solutions

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Whisper hangs on first run | Downloading 74MB model | Show "Downloading Whisper model..." message; set 5min timeout |
| `keyboard` requires admin | Windows input hook restriction | Use `keyboard.add_hotkey()` non-global or run as admin |
| pyttsx3 thread error on Windows | COM apartment threading | Only call `engine.runAndWait()` from main thread |
| sounddevice "no device" | PortAudio not found | Fall back to PyAudio; show "Check audio settings" error |
| spaCy model not found | Forgot `python -m spacy download` | Check on startup; add to setup script |
| File search too slow | Searching entire disk | Always restrict to `allowed_directories` from config |
| Clarification context lost | State not persisted between turns | `context.awaiting_clarification` must remain True until resolved |
| Volume control fails | No pycaw on Windows | Provide ctypes WinMM fallback |

---

*Implementation plan based on: PRD v1.0, Backend Schema v1.0, Appflow Specification, Frontend Guidelines v1.0, Tech Stack Specification v1.0*
