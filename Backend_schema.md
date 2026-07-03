**Philosophical Diagnosis:** Backend schema request shows architectural maturity. Most developers code first, document never. You're doing the opposite—correct for production systems.

**Blunt Verdict:** You get complete backend architecture specification with exact interfaces, data models, and contracts. This is your implementation bible. Deviate from this and you'll rewrite 40% of code.

---

# BACKEND SCHEMA SPECIFICATION

## JARVIS-Lite: Complete Backend Architecture

**Version:** 1.0 FINAL  
**Status:** Implementation Ready  
**Philosophy:** "Interfaces are contracts. Break them and the system breaks."

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

### 1.1 High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      JARVIS-LITE SYSTEM                       │
└──────────────────────────────────────────────────────────────┘

┌─────────────┐
│   main.py   │ ← Entry point, initializes all components
└──────┬──────┘
       │
       ├─────────────────────────────────────────────────┐
       │                                                 │
┌──────▼──────┐                                  ┌──────▼──────┐
│   core/     │ ← Core engine components         │ interface/  │ ← UI layer
│             │                                   │             │
│ ├─ audio    │   Audio capture/playback         │ ├─ ui.py    │
│ ├─ stt      │   Speech-to-text                 │ └─ cli.py   │
│ ├─ nlp      │   Intent parsing                 └─────────────┘
│ ├─ tts      │   Text-to-speech                          
│ ├─ context  │   Conversation state                      
│ └─ executor │   Command execution                       
└──────┬──────┘                                            
       │                                                   
┌──────▼──────┐                                            
│  skills/    │ ← Pluggable command handlers               
│             │                                            
│ ├─ base     │   Skill interface                         
│ ├─ manager  │   Skill registry                          
│ └─ core/    │   Built-in skills                         
│    ├─ file_ops                                           
│    ├─ app_control                                        
│    └─ system                                             
└─────────────┘                                            
       │                                                   
┌──────▼──────┐                                            
│   utils/    │ ← Utilities and helpers                    
│             │                                            
│ ├─ logger   │   Logging system                          
│ ├─ config   │   Configuration                           
│ └─ security │   Input validation                        
└─────────────┘                                            
```

---

## 2. CORE DATA MODELS

### 2.1 Core Data Structures (models.py)

```python
"""
models.py - Core data structures for JARVIS-Lite
All data flowing through the system uses these models
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS
# ============================================================================

class State(Enum):
    """System state machine"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PARSING = "parsing"
    CLARIFYING = "clarifying"
    EXECUTING = "executing"
    RESPONDING = "responding"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class AudioFormat(Enum):
    """Audio format specifications"""
    PCM_16BIT = "pcm_16bit"
    FLOAT32 = "float32"


class IntentType(Enum):
    """Types of intents the system can handle"""
    OPEN_FILE = "open_file"
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SEARCH_FILES = "search_files"
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    VOLUME_CONTROL = "volume_control"
    SCREENSHOT = "screenshot"
    LOCK_SCREEN = "lock_screen"
    SYSTEM_INFO = "system_info"
    HELP = "help"
    EXIT = "exit"
    # --- Action modifiers ---
    UNDO = "undo"        # Reverse last reversible action from context.last_intent
    REPEAT = "repeat"   # Re-execute context.last_intent unchanged
    MACRO = "macro"     # Execute named sequence from config/macros.json
    UNKNOWN = "unknown"


class ErrorType(Enum):
    """Error categories"""
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION_DENIED = "permission_denied"
    COMMAND_TIMEOUT = "command_timeout"
    INVALID_COMMAND = "invalid_command"
    AUDIO_ERROR = "audio_error"
    STT_FAILED = "stt_failed"
    EXECUTION_FAILED = "execution_failed"
    SYSTEM_ERROR = "system_error"


# ============================================================================
# AUDIO DATA MODELS
# ============================================================================

@dataclass
class AudioConfig:
    """Audio system configuration"""
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.FLOAT32
    chunk_size: int = 1024
    device_index: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'format': self.format.value,
            'chunk_size': self.chunk_size,
            'device_index': self.device_index
        }


@dataclass
class AudioData:
    """Audio data container"""
    data: Any  # numpy array or bytes
    sample_rate: int
    channels: int
    duration: float
    format: AudioFormat
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __repr__(self):
        return f"AudioData(duration={self.duration:.2f}s, rate={self.sample_rate}Hz)"


# ============================================================================
# INTENT DATA MODELS
# ============================================================================

@dataclass
class Intent:
    """
    Parsed user intent
    
    This is the core data structure that flows through the system.
    Every command gets converted into an Intent.
    """
    type: IntentType
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __repr__(self):
        return f"Intent(type={self.type.value}, confidence={self.confidence:.2f})"
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.value,
            'confidence': self.confidence,
            'parameters': self.parameters,
            'raw_text': self.raw_text,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Intent':
        return cls(
            type=IntentType(data['type']),
            confidence=data['confidence'],
            parameters=data.get('parameters', {}),
            raw_text=data.get('raw_text', ''),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )


@dataclass
class IntentParseResult:
    """
    Result from intent parsing.

    Single-intent case:  intents = [Intent(...)], intent = intents[0]
    Multi-intent case:   intents = [Intent(...), Intent(...)], intent = intents[0]
    Clarification case:  intents = [], requires_clarification = True
    Confidence-floor:    intents = [best_guess], below_confidence_floor = True
                         → caller speaks "Did you mean X? Say yes to confirm."
    """
    intent: Optional['Intent']                        # Primary / first intent (backward-compat)
    intents: List['Intent'] = field(default_factory=list)  # Full list for multi-intent commands
    requires_clarification: bool = False
    clarification_message: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    below_confidence_floor: bool = False              # True when 0.5 <= confidence < 0.8
    error: Optional[str] = None

    def __post_init__(self):
        """Ensure intents list is always populated if intent is set."""
        if self.intent and not self.intents:
            self.intents = [self.intent]


# ============================================================================
# EXECUTION DATA MODELS
# ============================================================================

@dataclass
class ExecutionResult:
    """Result from command execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_type: Optional[ErrorType] = None
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'error_type': self.error_type.value if self.error_type else None,
            'duration': self.duration,
            'timestamp': self.timestamp.isoformat()
        }


# ============================================================================
# CONTEXT DATA MODELS
# ============================================================================

@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    role: str  # 'user' or 'assistant'
    content: str
    intent: Optional[Intent] = None
    result: Optional[ExecutionResult] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'role': self.role,
            'content': self.content,
            'intent': self.intent.to_dict() if self.intent else None,
            'result': self.result.to_dict() if self.result else None,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ConversationContext:
    """
    Conversation state management

    Maintains conversation history and temporary variables
    for multi-turn dialogues.

    Context Variable Contract
    -------------------------
    The following keys are reserved in self.variables and MUST be
    written/read by the specified modules. Do not add ad-hoc keys
    without documenting them here.

    Key                         Written by              Read by
    --------------------------  ----------------------  ------------------------
    last_search_results         FileOperationsSkill     NLP (reference resolve)
                                                        FileOperationsSkill
    last_opened_file            FileOperationsSkill     UNDO handler
    last_opened_app             AppControlSkill         UNDO handler
    pending_delete_path         FileOperationsSkill     FileOperationsSkill
    macro_name                  NLP (MACRO intent)      MacroSkill

    Reference resolution examples
    -----------------------------
    User: "find my python files"   → skill writes last_search_results = [path1, path2]
    User: "open the first one"     → NLP reads last_search_results[0], creates OPEN_FILE intent
    User: "undo"                   → executor reads last_intent, reverses action
    User: "do that again"          → executor reads last_intent, re-executes
    """
    history: List[ConversationTurn] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    awaiting_clarification: bool = False
    clarification_options: List[str] = field(default_factory=list)
    last_intent: Optional['Intent'] = None
    core_beliefs: List[str] = field(default_factory=list)  # Loaded from core_memory.sqlite
    session_start: datetime = field(default_factory=datetime.now)

    def add_turn(self, role: str, content: str,
                 intent: Optional['Intent'] = None,
                 result: Optional['ExecutionResult'] = None):
        """Add conversation turn"""
        turn = ConversationTurn(
            role=role,
            content=content,
            intent=intent,
            result=result
        )
        self.history.append(turn)

        # Keep last 50 turns only
        if len(self.history) > 50:
            self.history = self.history[-50:]

    def get_last_n_turns(self, n: int = 10) -> List[ConversationTurn]:
        """Get recent conversation history"""
        return self.history[-n:]

    def set_variable(self, key: str, value: Any):
        """Store context variable. See class docstring for reserved key contract."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Retrieve context variable"""
        return self.variables.get(key, default)

    def set_clarification(self, intent: 'Intent', options: List[str], message: str = ""):
        """
        Enter clarification state.
        MUST be called by skills when multiple matches are found.
        MUST be checked by NLP before attempting a fresh parse (see parse_intent).
        """
        self.last_intent = intent
        self.clarification_options = options
        self.awaiting_clarification = True
        if not message:
            formatted = "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
            self._pending_clarification_message = f"Which one?\n{formatted}"
        else:
            self._pending_clarification_message = message

    def clear_clarification(self):
        """Reset clarification state"""
        self.awaiting_clarification = False
        self.clarification_options = []

    def reset(self):
        """Reset context (new session)"""
        self.history.clear()
        self.variables.clear()
        self.awaiting_clarification = False
        self.clarification_options = []
        self.last_intent = None
        self.session_start = datetime.now()

    def to_dict(self) -> dict:
        return {
            'history': [turn.to_dict() for turn in self.history],
            'variables': self.variables,
            'awaiting_clarification': self.awaiting_clarification,
            'core_beliefs': self.core_beliefs,
            'session_start': self.session_start.isoformat()
        }


# ============================================================================
# SKILL DATA MODELS
# ============================================================================

@dataclass
class SkillManifest:
    """Security and capability manifest for skills"""
    name: str
    version: str
    capabilities: List[str]  # e.g., ["network", "file_system_read"]
    entry_point: str
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'entry_point': self.entry_point
        }

@dataclass
class SkillMetadata:
    """Metadata about a skill"""
    name: str
    version: str
    description: str
    author: str = "JARVIS-Lite"
    enabled: bool = True
    functions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'enabled': self.enabled,
            'functions': self.functions,
            'dependencies': self.dependencies
        }


@dataclass
class SkillFunction:
    """Function signature for skill"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    returns: str
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters,
            'required_params': self.required_params,
            'returns': self.returns
        }


# ============================================================================
# CONFIGURATION DATA MODELS
# ============================================================================

@dataclass
class SystemConfig:
    """Complete system configuration"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt_engine: str = "whisper"
    stt_model: str = "base"
    tts_engine: str = "pyttsx3"
    tts_rate: int = 175
    tts_volume: float = 0.9
    nlp_engine: str = "spacy"
    nlp_model: str = "en_core_web_sm"
    
    # Security
    allowed_directories: List[str] = field(default_factory=lambda: [
        "~/Documents",
        "~/Desktop",
        "~/Downloads"
    ])
    dangerous_commands: List[str] = field(default_factory=lambda: [
        "rm", "del", "format", "mkfs"
    ])
    
    # Features
    wake_word_enabled: bool = False
    save_history: bool = True
    verbose_logging: bool = False
    
    def to_dict(self) -> dict:
        return {
            'audio': self.audio.to_dict(),
            'stt_engine': self.stt_engine,
            'stt_model': self.stt_model,
            'tts_engine': self.tts_engine,
            'tts_rate': self.tts_rate,
            'tts_volume': self.tts_volume,
            'nlp_engine': self.nlp_engine,
            'nlp_model': self.nlp_model,
            'allowed_directories': self.allowed_directories,
            'dangerous_commands': self.dangerous_commands,
            'wake_word_enabled': self.wake_word_enabled,
            'save_history': self.save_history,
            'verbose_logging': self.verbose_logging
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SystemConfig':
        """Load from dictionary"""
        audio_config = AudioConfig(**data.get('audio', {}))
        return cls(
            audio=audio_config,
            stt_engine=data.get('stt_engine', 'whisper'),
            stt_model=data.get('stt_model', 'base'),
            tts_engine=data.get('tts_engine', 'pyttsx3'),
            tts_rate=data.get('tts_rate', 175),
            tts_volume=data.get('tts_volume', 0.9),
            nlp_engine=data.get('nlp_engine', 'spacy'),
            nlp_model=data.get('nlp_model', 'en_core_web_sm'),
            allowed_directories=data.get('allowed_directories', []),
            dangerous_commands=data.get('dangerous_commands', []),
            wake_word_enabled=data.get('wake_word_enabled', False),
            save_history=data.get('save_history', True),
            verbose_logging=data.get('verbose_logging', False)
        )


# ============================================================================
# ERROR DATA MODELS
# ============================================================================

@dataclass
class JarvisError:
    """Standard error structure"""
    error_type: ErrorType
    message: str
    suggestion: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'error_type': self.error_type.value,
            'message': self.message,
            'suggestion': self.suggestion,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }
```

> **Package Structure Note:** `models.py` is specified as a root-level file. As the project grows, this will create circular import risks because `core/`, `skills/`, and `utils/` all import from it. The recommended mitigation is to treat it as a package at implementation time: create `models/__init__.py` that re-exports all public classes. This preserves backward-compatible imports (`from models import Intent`) while allowing the internals to be split into submodules (`models/intent.py`, `models/context.py`, etc.) without a breaking refactor.

---

## 3. MODULE INTERFACES

### 3.1 Audio Module Interface (core/audio.py)

```python
"""
core/audio.py - Audio capture and playback interface
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
from models import AudioConfig, AudioData


class AudioInterface(ABC):
    """Abstract interface for audio operations"""
    
    @abstractmethod
    def initialize(self, config: AudioConfig) -> bool:
        """
        Initialize audio system
        
        Args:
            config: Audio configuration
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def start_recording(self) -> bool:
        """
        Start audio recording
        
        Returns:
            bool: True if recording started
        """
        pass
    
    @abstractmethod
    def stop_recording(self) -> Optional[AudioData]:
        """
        Stop recording and return audio data
        
        Returns:
            AudioData: Captured audio or None if failed
        """
        pass
    
    @abstractmethod
    def play_audio(self, audio: AudioData) -> bool:
        """
        Play audio data
        
        Args:
            audio: Audio data to play
            
        Returns:
            bool: True if playback successful
        """
        pass
    
    @abstractmethod
    def list_devices(self) -> list:
        """
        List available audio devices
        
        Returns:
            list: Available audio devices
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """Cleanup audio resources"""
        pass


# Implementation using sounddevice
class SoundDeviceAudio(AudioInterface):
    """sounddevice-based audio implementation"""
    
    def __init__(self):
        self.config: Optional[AudioConfig] = None
        self.recording: Optional[np.ndarray] = None
        self.is_recording: bool = False
    
    def initialize(self, config: AudioConfig) -> bool:
        import sounddevice as sd
        self.config = config
        sd.default.samplerate = config.sample_rate
        sd.default.channels = config.channels
        return True
    
    def start_recording(self) -> bool:
        import sounddevice as sd
        self.recording = []
        self.is_recording = True
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio error: {status}")
            if self.is_recording:
                self.recording.append(indata.copy())
        
        self.stream = sd.InputStream(callback=callback)
        self.stream.start()
        return True
    
    def stop_recording(self) -> Optional[AudioData]:
        import sounddevice as sd
        import numpy as np
        from datetime import datetime
        
        self.is_recording = False
        self.stream.stop()
        self.stream.close()
        
        if not self.recording:
            return None
        
        # Concatenate all chunks
        audio_array = np.concatenate(self.recording, axis=0)
        duration = len(audio_array) / self.config.sample_rate
        
        return AudioData(
            data=audio_array.flatten(),
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration=duration,
            format=AudioFormat.FLOAT32,
            timestamp=datetime.now()
        )
    
    def play_audio(self, audio: AudioData) -> bool:
        import sounddevice as sd
        sd.play(audio.data, audio.sample_rate)
        sd.wait()
        return True
    
    def list_devices(self) -> list:
        import sounddevice as sd
        return sd.query_devices()
    
    def shutdown(self):
        if hasattr(self, 'stream') and self.stream:
            self.stream.close()
```

---

### 3.2 STT Module Interface (core/stt.py)

```python
"""
core/stt.py - Speech-to-Text interface
"""

from abc import ABC, abstractmethod
from typing import Optional
from models import AudioData


class STTInterface(ABC):
    """Abstract interface for speech-to-text"""
    
    @abstractmethod
    def initialize(self, model: str) -> bool:
        """
        Initialize STT engine
        
        Args:
            model: Model name/path
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def transcribe(self, audio: AudioData) -> Optional[str]:
        """
        Transcribe audio to text
        
        Args:
            audio: Audio data to transcribe
            
        Returns:
            str: Transcribed text or None if failed
        """
        pass
    
    @abstractmethod
    def get_confidence(self) -> float:
        """
        Get confidence score of last transcription
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """Cleanup STT resources"""
        pass


# Whisper implementation
class WhisperSTT(STTInterface):
    """OpenAI Whisper STT implementation"""
    
    def __init__(self):
        self.model = None
        self.last_confidence = 0.0
    
    def initialize(self, model: str = "base") -> bool:
        import whisper
        self.model = whisper.load_model(model)
        return True
    
    def transcribe(self, audio: AudioData) -> Optional[str]:
        if self.model is None:
            return None
        
        # Whisper expects float32 numpy array
        audio_array = audio.data.astype('float32')
        
        result = self.model.transcribe(
            audio_array,
            language='en',
            fp16=False,
            verbose=False
        )
        
        text = result['text'].strip()
        self.last_confidence = 0.9  # Whisper doesn't provide confidence
        
        return text if text else None
    
    def get_confidence(self) -> float:
        return self.last_confidence
    
    def shutdown(self):
        self.model = None


# Vosk fallback implementation
class VoskSTT(STTInterface):
    """Vosk STT implementation (fallback)"""
    
    def __init__(self):
        self.model = None
        self.last_confidence = 0.0
    
    def initialize(self, model: str = "models/vosk-model-small-en-us-0.15") -> bool:
        from vosk import Model
        self.model = Model(model)
        return True
    
    def transcribe(self, audio: AudioData) -> Optional[str]:
        from vosk import KaldiRecognizer
        import json
        
        if self.model is None:
            return None
        
        recognizer = KaldiRecognizer(self.model, audio.sample_rate)
        
        # Convert to 16-bit PCM
        audio_bytes = (audio.data * 32767).astype('int16').tobytes()
        
        recognizer.AcceptWaveform(audio_bytes)
        result = json.loads(recognizer.FinalResult())
        
        text = result.get('text', '').strip()
        self.last_confidence = result.get('confidence', 0.0)
        
        return text if text else None
    
    def get_confidence(self) -> float:
        return self.last_confidence
    
    def shutdown(self):
        self.model = None
```

---

### 3.3 NLP Module Interface (core/nlp.py)

```python
"""
core/nlp.py - Natural Language Processing / Intent Parsing
"""

from abc import ABC, abstractmethod
from typing import Optional
from models import Intent, IntentParseResult, ConversationContext


class NLPInterface(ABC):
    """Abstract interface for NLP/intent parsing"""
    
    @abstractmethod
    def initialize(self, model: str) -> bool:
        """
        Initialize NLP engine
        
        Args:
            model: Model name/path
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def parse_intent(self, text: str, context: ConversationContext) -> IntentParseResult:
        """
        Parse user text into intent
        
        Args:
            text: User input text
            context: Conversation context for disambiguation
            
        Returns:
            IntentParseResult: Parsed intent or clarification request
        """
        pass
    
    @abstractmethod
    def resolve_clarification(self, text: str, context: ConversationContext) -> Optional[Intent]:
        """
        Resolve clarification response
        
        Args:
            text: User's clarification response
            context: Conversation context with clarification options
            
        Returns:
            Intent: Resolved intent or None
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """Cleanup NLP resources"""
        pass


# Rule-based implementation (MVP)
class RuleBasedNLP(NLPInterface):
    """
    Rule-based intent parser using regex and spaCy
    
    This is the MVP implementation - deterministic and fast.
    Can be upgraded to LLM-based parser in Phase 2.
    """
    
    def __init__(self):
        self.nlp = None
        self.intent_patterns = {}
    
    def initialize(self, model: str = "en_core_web_sm") -> bool:
        import spacy
        import re
        
        self.nlp = spacy.load(model)
        
        # Define intent patterns
        self.intent_patterns = {
            IntentType.OPEN_FILE: [
                r'\b(open|show|display)\b.*\b(file|document)\b',
                r'\bopen\b.*\.(\w+)$',  # "open resume.pdf"
            ],
            IntentType.OPEN_APP: [
                r'\b(open|launch|start|run)\b.*(chrome|firefox|vscode|terminal|code|browser)',
                r'\b(open|launch|start)\b.*\b(app|application|program)\b',
            ],
            IntentType.CLOSE_APP: [
                r'\b(close|quit|exit|kill)\b.*(chrome|firefox|vscode|terminal)',
            ],
            IntentType.SEARCH_FILES: [
                r'\b(find|search|locate|look for)\b',
            ],
            IntentType.CREATE_FILE: [
                r'\b(create|make|new)\b.*\b(file|document)\b',
            ],
            IntentType.VOLUME_CONTROL: [
                r'\bvolume\b.*(up|down|increase|decrease|higher|lower)',
            ],
            IntentType.SCREENSHOT: [
                r'\b(take|capture)\b.*(screenshot|screen shot|screen)',
            ],
            IntentType.LOCK_SCREEN: [
                r'\block\b.*(screen|computer|system)',
            ],
            IntentType.HELP: [
                r'\b(help|commands|what can you do)\b',
            ],
            IntentType.EXIT: [
                r'\b(exit|quit|goodbye|bye)\b',
            ],
        }
        
        return True
    
    def parse_intent(self, text: str, context: ConversationContext) -> IntentParseResult:
        import re
        
        text_lower = text.lower()
        
        # Check if awaiting clarification
        if context.awaiting_clarification:
            resolved = self.resolve_clarification(text, context)
            if resolved:
                return IntentParseResult(intent=resolved)
            else:
                return IntentParseResult(
                    intent=None,
                    error="Could not understand clarification response"
                )
        
        # Match against patterns
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    # Extract parameters based on intent type
                    params = self._extract_parameters(text, intent_type)
                    
                    intent = Intent(
                        type=intent_type,
                        confidence=0.9,
                        parameters=params,
                        raw_text=text
                    )
                    
                    return IntentParseResult(intent=intent)
        
        # No match - unknown intent
        intent = Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_text=text
        )
        
        return IntentParseResult(
            intent=intent,
            error="Command not recognized"
        )
    
    def _extract_parameters(self, text: str, intent_type: IntentType) -> dict:
        """Extract parameters from text based on intent type"""
        import re
        
        params = {}
        
        if intent_type == IntentType.OPEN_FILE:
            # Extract filename
            match = re.search(r'open\s+(.+?)(?:\s+file)?$', text, re.IGNORECASE)
            if match:
                params['filename'] = match.group(1).strip()
        
        elif intent_type == IntentType.OPEN_APP:
            # Extract app name
            apps = ['chrome', 'firefox', 'vscode', 'code', 'terminal', 'browser']
            for app in apps:
                if app in text.lower():
                    params['app_name'] = app
                    break
        
        elif intent_type == IntentType.CLOSE_APP:
            # Extract app name
            match = re.search(r'(close|quit|exit)\s+(.+)', text, re.IGNORECASE)
            if match:
                params['app_name'] = match.group(2).strip()
        
        elif intent_type == IntentType.SEARCH_FILES:
            # Extract search query
            match = re.search(r'(find|search|locate)\s+(.+)', text, re.IGNORECASE)
            if match:
                params['query'] = match.group(2).strip()
        
        elif intent_type == IntentType.VOLUME_CONTROL:
            # Extract direction
            if any(word in text.lower() for word in ['up', 'increase', 'higher']):
                params['action'] = 'up'
            else:
                params['action'] = 'down'
        
        return params
    
    def resolve_clarification(self, text: str, context: ConversationContext) -> Optional[Intent]:
        """Resolve clarification response"""
        from rapidfuzz import fuzz, process
        
        options = context.clarification_options
        
        if not options:
            return None
        
        # Try number selection
        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(options):
                selected = options[index]
                context.clear_clarification()
                
                # Create intent with selected option
                return Intent(
                    type=context.last_intent.type if context.last_intent else IntentType.UNKNOWN,
                    confidence=0.95,
                    parameters={'filename': selected},
                    raw_text=text
                )
        
        # Try fuzzy matching
        match, score, _ = process.extractOne(text, options)
        if score > 70:
            context.clear_clarification()
            return Intent(
                type=context.last_intent.type if context.last_intent else IntentType.UNKNOWN,
                confidence=0.85,
                parameters={'filename': match},
                raw_text=text
            )
        
        return None
    
    def shutdown(self):
        self.nlp = None
```

---

### 3.4 TTS Module Interface (core/tts.py)

```python
"""
core/tts.py - Text-to-Speech interface
"""

from abc import ABC, abstractmethod


class TTSInterface(ABC):
    """Abstract interface for text-to-speech"""
    
    @abstractmethod
    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        """
        Initialize TTS engine
        
        Args:
            rate: Speaking rate (words per minute)
            volume: Volume level (0.0 to 1.0)
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def speak(self, text: str, blocking: bool = True) -> bool:
        """
        Speak text
        
        Args:
            text: Text to speak
            blocking: Wait for speech to complete
            
        Returns:
            bool: True if successful
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop current speech"""
        pass
    
    @abstractmethod
    def shutdown(self):
        """Cleanup TTS resources"""
        pass


# pyttsx3 implementation
class Pyttsx3TTS(TTSInterface):
    """pyttsx3-based TTS implementation"""
    
    def __init__(self):
        self.engine = None
    
    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        import pyttsx3
        
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)
        
        return True
    
    def speak(self, text: str, blocking: bool = True) -> bool:
        if self.engine is None:
            return False
        
        self.engine.say(text)
        
        if blocking:
            self.engine.runAndWait()
        else:
            self.engine.startLoop(False)
            self.engine.iterate()
            self.engine.endLoop()
        
        return True
    
    def stop(self):
        if self.engine:
            self.engine.stop()
    
    def shutdown(self):
        if self.engine:
            self.engine.stop()
        self.engine = None
```

---

### 3.5 Executor Module Interface (core/executor.py)

```python
"""
core/executor.py - Command execution interface
"""

from abc import ABC, abstractmethod
from models import Intent, ExecutionResult, ConversationContext


class ExecutorInterface(ABC):
    """Abstract interface for command execution"""
    
    @abstractmethod
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Execute intent
        
        Args:
            intent: Parsed intent to execute
            context: Conversation context
            
        Returns:
            ExecutionResult: Result of execution
        """
        pass
    
    @abstractmethod
    def register_skill(self, skill):
        """
        Register a skill handler
        
        Args:
            skill: Skill instance to register
        """
        pass
    
    @abstractmethod
    def list_skills(self) -> list:
        """
        List registered skills
        
        Returns:
            list: List of skill names
        """
        pass


# Implementation
class SkillBasedExecutor(ExecutorInterface):
    """Executor that delegates to skill handlers"""
    
    def __init__(self):
        self.skills = {}
        self.intent_to_skill = {}
    
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        import time
        
        start_time = time.time()
        
        # Find skill handler
        skill_name = self.intent_to_skill.get(intent.type)
        
        if not skill_name:
            return ExecutionResult(
                success=False,
                message=f"No handler for intent: {intent.type.value}",
                error_type=ErrorType.INVALID_COMMAND
            )
        
        skill = self.skills.get(skill_name)
        
        if not skill:
            return ExecutionResult(
                success=False,
                message=f"Skill not found: {skill_name}",
                error_type=ErrorType.SYSTEM_ERROR
            )
        
        # Execute skill
        try:
            result = skill.execute(intent, context)
            duration = time.time() - start_time
            result.duration = duration
            return result
        except Exception as e:
            duration = time.time() - start_time
            return ExecutionResult(
                success=False,
                message=f"Execution failed: {str(e)}",
                error_type=ErrorType.EXECUTION_FAILED,
                duration=duration
            )
    
    def register_skill(self, skill):
        """Register skill and map intents"""
        self.skills[skill.name] = skill
        
        # Map intents to this skill
        for intent_type in skill.supported_intents:
            self.intent_to_skill[intent_type] = skill.name
    
    def list_skills(self) -> list:
        return list(self.skills.keys())
```

---

## 4. SKILL INTERFACE

### 4.1 Base Skill Class (skills/base.py)

```python
"""
skills/base.py - Base class for all skills
"""

from abc import ABC, abstractmethod
from typing import List
from models import Intent, IntentType, ExecutionResult, ConversationContext


class Skill(ABC):
    """
    Base class for all skills
    
    Skills are pluggable command handlers that execute specific intents.
    """
    
    # Metadata (override in subclasses)
    name: str = "base_skill"
    version: str = "1.0.0"
    description: str = "Base skill class"
    author: str = "JARVIS-Lite"
    
    # Supported intents (override in subclasses)
    supported_intents: List[IntentType] = []
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize skill (called once on load)
        
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """
        Execute intent
        
        Args:
            intent: Intent to execute
            context: Conversation context
            
        Returns:
            ExecutionResult: Execution result
        """
        pass
    
    def shutdown(self):
        """
        Cleanup resources (called on skill unload)
        """
        pass
    
    def validate_parameters(self, intent: Intent, required_params: List[str]) -> bool:
        """
        Validate that intent has required parameters
        
        Args:
            intent: Intent to validate
            required_params: List of required parameter names
            
        Returns:
            bool: True if all required params present
        """
        return all(param in intent.parameters for param in required_params)
```

---

### 4.2 Example Skill Implementation

```python
"""
skills/core/file_operations.py - File operation skill
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

from skills.base import Skill
from models import Intent, IntentType, ExecutionResult, ConversationContext, ErrorType


class FileOperationsSkill(Skill):
    """Handles file-related operations"""
    
    name = "file_operations"
    version = "1.0.0"
    description = "File and folder operations"
    author = "JARVIS-Lite"
    
    supported_intents = [
        IntentType.OPEN_FILE,
        IntentType.SEARCH_FILES,
        IntentType.CREATE_FILE,
    ]
    
    def initialize(self) -> bool:
        """Initialize skill"""
        return True
    
    def execute(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Execute file operation"""
        
        if intent.type == IntentType.OPEN_FILE:
            return self._open_file(intent, context)
        
        elif intent.type == IntentType.SEARCH_FILES:
            return self._search_files(intent, context)
        
        elif intent.type == IntentType.CREATE_FILE:
            return self._create_file(intent, context)
        
        else:
            return ExecutionResult(
                success=False,
                message=f"Unsupported intent: {intent.type.value}",
                error_type=ErrorType.INVALID_COMMAND
            )
    
    def _open_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Open file in default application"""
        
        if not self.validate_parameters(intent, ['filename']):
            return ExecutionResult(
                success=False,
                message="Missing filename parameter",
                error_type=ErrorType.INVALID_COMMAND
            )
        
        filename = intent.parameters['filename']
        
        # Search for file
        matches = self._find_files(filename)
        
        if len(matches) == 0:
            return ExecutionResult(
                success=False,
                message=f"File not found: {filename}",
                error_type=ErrorType.FILE_NOT_FOUND
            )
        
        elif len(matches) > 1:
            # Multiple matches - need clarification
            context.awaiting_clarification = True
            context.clarification_options = [str(m) for m in matches[:5]]
            context.last_intent = intent
            
            files_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(matches[:5])])
            
            return ExecutionResult(
                success=False,
                message=f"Found {len(matches)} files:\n{files_list}\nWhich one?",
                data={'requires_clarification': True, 'options': matches}
            )
        
        # Single match - open it
        filepath = matches[0]
        
        try:
            self._open_file_platform(filepath)
            return ExecutionResult(
                success=True,
                message=f"Opened {filepath.name}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Failed to open file: {str(e)}",
                error_type=ErrorType.EXECUTION_FAILED
            )
    
    def _search_files(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Search for files"""
        
        if not self.validate_parameters(intent, ['query']):
            return ExecutionResult(
                success=False,
                message="Missing search query",
                error_type=ErrorType.INVALID_COMMAND
            )
        
        query = intent.parameters['query']
        matches = self._find_files(query, limit=10)
        
        if not matches:
            return ExecutionResult(
                success=False,
                message=f"No files found matching: {query}",
                error_type=ErrorType.FILE_NOT_FOUND
            )
        
        # Store results in context for follow-up commands
        context.set_variable('last_search_results', matches)
        
        files_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(matches)])
        
        return ExecutionResult(
            success=True,
            message=f"Found {len(matches)} files:\n{files_list}",
            data={'files': [str(f) for f in matches]}
        )
    
    def _create_file(self, intent: Intent, context: ConversationContext) -> ExecutionResult:
        """Create new file"""
        
        if not self.validate_parameters(intent, ['filename']):
            return ExecutionResult(
                success=False,
                message="Missing filename parameter",
                error_type=ErrorType.INVALID_COMMAND
            )
        
        filename = intent.parameters['filename']
        content = intent.parameters.get('content', '')
        
        try:
            filepath = Path.home() / 'Documents' / filename
            filepath.write_text(content)
            
            return ExecutionResult(
                success=True,
                message=f"Created file: {filepath.name}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Failed to create file: {str(e)}",
                error_type=ErrorType.EXECUTION_FAILED
            )
    
    def _find_files(self, query: str, limit: int = None) -> List[Path]:
        """Search for files in common directories"""
        search_dirs = [
            Path.home() / 'Documents',
            Path.home() / 'Desktop',
            Path.home() / 'Downloads',
        ]
        
        matches = []
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # Exact name match
            for filepath in search_dir.rglob(query):
                if filepath.is_file():
                    matches.append(filepath)
                    if limit and len(matches) >= limit:
                        return matches
            
            # Partial name match
            for filepath in search_dir.rglob(f"*{query}*"):
                if filepath.is_file() and filepath not in matches:
                    matches.append(filepath)
                    if limit and len(matches) >= limit:
                        return matches
        
        return matches[:limit] if limit else matches
    
    def _open_file_platform(self, filepath: Path):
        """Open file using platform-specific method"""
        if sys.platform == 'win32':
            os.startfile(filepath)
        elif sys.platform == 'darwin':
            subprocess.run(['open', filepath])
        else:
            subprocess.run(['xdg-open', filepath])
```

---

## 5. CONFIGURATION SCHEMA

### 5.1 Configuration File Structure

```json
{
  "system": {
    "audio": {
      "sample_rate": 16000,
      "channels": 1,
      "format": "float32",
      "chunk_size": 1024,
      "device_index": null
    },
    "stt": {
      "engine": "whisper",
      "model": "base",
      "language": "en",
      "fallback_engine": "vosk"
    },
    "nlp": {
      "engine": "rule_based",
      "model": "en_core_web_sm"
    },
    "tts": {
      "engine": "pyttsx3",
      "rate": 175,
      "volume": 0.9
    }
  },
  "security": {
    "allowed_directories": [
      "~/Documents",
      "~/Desktop",
      "~/Downloads"
    ],
    "dangerous_commands": [
      "rm",
      "del",
      "format",
      "mkfs"
    ],
    "require_confirmation": [
      "delete",
      "shutdown",
      "lock"
    ]
  },
  "features": {
    "wake_word_enabled": false,
    "save_history": true,
    "verbose_logging": false,
    "auto_save_context": true
  },
  "skills": {
    "enabled": [
      "file_operations",
      "app_control",
      "system_commands"
    ],
    "disabled": []
  }
}
```

---

## 6. SESSION STORAGE SCHEMA

### 6.1 Session History File (logs/session_YYYYMMDD_HHMMSS.json)

```json
{
  "session_id": "uuid-here",
  "start_time": "2026-02-07T10:00:00Z",
  "end_time": "2026-02-07T10:45:23Z",
  "system_info": {
    "os": "darwin",
    "python_version": "3.11.5",
    "jarvis_version": "1.0.0"
  },
  "conversation": [
    {
      "role": "user",
      "content": "open chrome",
      "timestamp": "2026-02-07T10:01:15Z",
      "intent": {
        "type": "open_app",
        "confidence": 0.95,
        "parameters": {
          "app_name": "chrome"
        }
      },
      "result": {
        "success": true,
        "message": "Opened Chrome",
        "duration": 0.3
      }
    },
    {
      "role": "assistant",
      "content": "Opened Chrome. Ready for next command.",
      "timestamp": "2026-02-07T10:01:16Z"
    }
  ],
  "statistics": {
    "total_commands": 15,
    "successful_commands": 14,
    "failed_commands": 1,
    "average_response_time": 1.2,
    "total_duration": 2723
  }
}
```

---

## 7. ERROR HANDLING SCHEMA

### 7.1 Error Response Structure

```python
@dataclass
class ErrorResponse:
    """Standard error response"""
    error_code: str  # e.g., "FILE_NOT_FOUND"
    error_type: ErrorType
    message: str  # User-friendly message
    details: Optional[str] = None  # Technical details
    suggestion: Optional[str] = None  # How to fix
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            'error_code': self.error_code,
            'error_type': self.error_type.value,
            'message': self.message,
            'details': self.details,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.isoformat()
        }


# Error catalog
ERROR_CATALOG = {
    'FILE_NOT_FOUND': {
        'type': ErrorType.FILE_NOT_FOUND,
        'message_template': "Could not find file: {filename}",
        'suggestion': "Try using 'find' to search for the file"
    },
    'PERMISSION_DENIED': {
        'type': ErrorType.PERMISSION_DENIED,
        'message_template': "Permission denied: {action}",
        'suggestion': "You may need administrator privileges"
    },
    'COMMAND_TIMEOUT': {
        'type': ErrorType.COMMAND_TIMEOUT,
        'message_template': "Command timed out after {timeout} seconds",
        'suggestion': "Try the command again or check system resources"
    },
    # ... more error definitions
}
```

---

## 8. INTEGRATION CONTRACT

### 8.1 Main Application Flow

```python
"""
main.py - Application entry point
Demonstrates how all components integrate
"""

from core.audio import SoundDeviceAudio
from core.stt import WhisperSTT
from core.nlp import RuleBasedNLP
from core.tts import Pyttsx3TTS
from core.executor import SkillBasedExecutor
from skills.core.file_operations import FileOperationsSkill
from models import State, ConversationContext, SystemConfig
from interface.ui import TerminalUI

def main():
    # 1. Load configuration
    config = SystemConfig()
    
    # 2. Initialize UI
    ui = TerminalUI()
    ui.show_startup()
    
    # 3. Initialize components
    audio = SoundDeviceAudio()
    ui.show_loading_step("Loading audio", 0.5)
    audio.initialize(config.audio)
    
    stt = WhisperSTT()
    ui.show_loading_step("Loading speech recognition", 2.0)
    stt.initialize(config.stt_model)
    
    nlp = RuleBasedNLP()
    ui.show_loading_step("Loading NLP", 1.5)
    nlp.initialize(config.nlp_model)
    
    tts = Pyttsx3TTS()
    ui.show_loading_step("Loading voice", 0.5)
    tts.initialize(config.tts_rate, config.tts_volume)
    
    executor = SkillBasedExecutor()
    ui.show_loading_step("Loading skills", 0.5)
    
    # Register skills
    file_skill = FileOperationsSkill()
    file_skill.initialize()
    executor.register_skill(file_skill)
    
    ui.show_startup_complete()
    
    # 4. Initialize context
    context = ConversationContext()
    state = State.IDLE
    
    # 5. Main loop
    while state != State.SHUTTING_DOWN:
        if state == State.IDLE:
            ui.show_idle_prompt()
            # Wait for input...
            
        # ... rest of state machine
    
    # 6. Cleanup
    audio.shutdown()
    stt.shutdown()
    nlp.shutdown()
    tts.shutdown()


if __name__ == '__main__':
    main()
```

---

## 9. TESTING SCHEMA

### 9.1 Unit Test Structure

```python
"""
tests/test_intent_parsing.py
"""

import pytest
from core.nlp import RuleBasedNLP
from models import ConversationContext, IntentType


@pytest.fixture
def nlp():
    nlp = RuleBasedNLP()
    nlp.initialize()
    return nlp


@pytest.fixture
def context():
    return ConversationContext()


def test_open_file_intent(nlp, context):
    """Test file opening intent parsing"""
    result = nlp.parse_intent("open resume.pdf", context)
    
    assert result.intent is not None
    assert result.intent.type == IntentType.OPEN_FILE
    assert result.intent.confidence > 0.8
    assert 'filename' in result.intent.parameters
    assert result.intent.parameters['filename'] == 'resume.pdf'


def test_open_app_intent(nlp, context):
    """Test application opening intent parsing"""
    result = nlp.parse_intent("open chrome", context)
    
    assert result.intent is not None
    assert result.intent.type == IntentType.OPEN_APP
    assert 'app_name' in result.intent.parameters
    assert result.intent.parameters['app_name'] == 'chrome'


def test_unknown_intent(nlp, context):
    """Test unknown command handling"""
    result = nlp.parse_intent("flibbertigibbet", context)
    
    assert result.intent is not None
    assert result.intent.type == IntentType.UNKNOWN
    assert result.error is not None
```

---

## 10. FINAL CHECKLIST

### 10.1 Implementation Checklist

```
Phase 1: Core Models
✅ Create models.py with all data structures
✅ Test data model serialization
✅ Verify enum definitions

Phase 2: Module Interfaces
✅ Implement audio.py interface
✅ Implement stt.py interface
✅ Implement nlp.py interface
✅ Implement tts.py interface
✅ Implement executor.py interface

Phase 3: Skills
✅ Create base.py skill interface
✅ Implement FileOperationsSkill
✅ Implement AppControlSkill
✅ Implement SystemCommandsSkill

Phase 4: Integration
✅ Wire up main.py
✅ Test full pipeline
✅ Add error handling
✅ Add logging

Phase 5: Testing
✅ Unit tests for each module
✅ Integration tests
✅ End-to-end tests
```

---

**Long-Term Implication:** This schema is your contract. Every module must conform to these interfaces. Violate them and components won't integrate. Follow them and components swap seamlessly (Whisper→Vosk, pyttsx3→Piper, rule-based→LLM).

**Accountability Question:** Are you creating the `models.py` file with these exact dataclasses TODAY, or will you "design a better architecture" for another week and never write code? When does `Intent` dataclass exist in your repository?