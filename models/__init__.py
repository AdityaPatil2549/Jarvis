"""
models/__init__.py - Core data structures for JARVIS-Lite
All data flowing through the system uses these models.

Source of truth: Backend_schema.md §2.1
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS
# ============================================================================

class State(Enum):
    """System state machine (Appflow §2)"""
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
    UNDO = "undo"          # Reverse last reversible action from context.last_intent
    REPEAT = "repeat"      # Re-execute context.last_intent unchanged
    MACRO = "macro"        # Execute named sequence from config/macros.json
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
    Parsed user intent.

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
    intent: Optional['Intent']
    intents: List['Intent'] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_message: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    below_confidence_floor: bool = False
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
    Conversation state management.

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
    """
    history: List[ConversationTurn] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    awaiting_clarification: bool = False
    clarification_options: List[str] = field(default_factory=list)
    last_intent: Optional['Intent'] = None
    core_beliefs: List[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.now)

    def add_turn(self, role: str, content: str,
                 intent: Optional['Intent'] = None,
                 result: Optional['ExecutionResult'] = None):
        """Add conversation turn, auto-prune to last 50."""
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
        MUST be checked by NLP before attempting a fresh parse.
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
    capabilities: List[str] = field(default_factory=list)
    entry_point: str = ""

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
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    returns: str = ""

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
    stt_engine: str = "faster-whisper"
    stt_model: str = "base"
    tts_engine: str = "kokoro"
    tts_rate: int = 175
    tts_volume: float = 0.9
    tts_voice: str = "af_heart"   # Kokoro voice ID
    tts_lang_code: str = "a"      # 'a'=American, 'b'=British
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
            'tts_voice': self.tts_voice,
            'tts_lang_code': self.tts_lang_code,
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
        audio_data = data.get('audio', {})
        audio_config = AudioConfig(
            sample_rate=audio_data.get('sample_rate', 16000),
            channels=audio_data.get('channels', 1),
            chunk_size=audio_data.get('chunk_size', 1024),
            device_index=audio_data.get('device_index')
        )
        return cls(
            audio=audio_config,
            stt_engine=data.get('stt_engine', 'faster-whisper'),
            stt_model=data.get('stt_model', 'base'),
            tts_engine=data.get('tts_engine', 'kokoro'),
            tts_rate=data.get('tts_rate', 175),
            tts_volume=data.get('tts_volume', 0.9),
            tts_voice=data.get('tts_voice', 'af_heart'),
            tts_lang_code=data.get('tts_lang_code', 'a'),
            nlp_engine=data.get('nlp_engine', 'spacy'),
            nlp_model=data.get('nlp_model', 'en_core_web_sm'),
            allowed_directories=data.get('allowed_directories', [
                "~/Documents", "~/Desktop", "~/Downloads"
            ]),
            dangerous_commands=data.get('dangerous_commands', [
                "rm", "del", "format", "mkfs"
            ]),
            wake_word_enabled=data.get('wake_word_enabled', False),
            save_history=data.get('save_history', True),
            verbose_logging=data.get('verbose_logging', False),
        )


# ============================================================================
# ERROR DATA MODELS
# ============================================================================

@dataclass
class JarvisError:
    """Typed error with user-facing suggestion"""
    error_type: ErrorType
    message: str
    suggestion: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            'error_type': self.error_type.value,
            'message': self.message,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.isoformat()
        }
