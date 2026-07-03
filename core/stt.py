"""
core/stt.py - Speech-to-Text for JARVIS-Lite.
Implements STTInterface ABC + WhisperSTT + VoskSTT fallback.

Source of truth: Backend_schema.md §3.2, Implementation_plan.md §3.5
"""

from abc import ABC, abstractmethod
from typing import Optional

from models import AudioData
from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class STTInterface(ABC):
    """Abstract interface for speech-to-text engines."""

    @abstractmethod
    def initialize(self, model: str = "base") -> bool:
        """Load STT model. Return True if ready."""
        pass

    @abstractmethod
    def transcribe(self, audio: AudioData) -> Optional[str]:
        """
        Transcribe audio to text.
        Returns None if transcription fails or produces empty text.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up STT resources."""
        pass


# ============================================================================
# WHISPER IMPLEMENTATION (PRIMARY)
# ============================================================================

class WhisperSTT(STTInterface):
    """OpenAI Whisper speech-to-text engine (primary)."""

    def __init__(self):
        self.model = None
        self.model_name: str = "base"
        self.last_confidence: float = 0.0
        self._loaded = False

    def initialize(self, model: str = "base") -> bool:
        """
        Load Whisper model. Cached after first load (~74MB download).
        Model sizes: tiny(39M), base(74M), small(244M), medium(769M), large(1550M)
        """
        self.model_name = model
        try:
            import whisper
            logger.info(f"Loading Whisper model: {model}", component="stt")
            self.model = whisper.load_model(model)
            self._loaded = True
            logger.info(f"Whisper model '{model}' loaded successfully",
                        component="stt")
            return True
        except ImportError:
            logger.error("openai-whisper not installed. Run: pip install openai-whisper",
                         component="stt")
            return False
        except Exception as e:
            logger.error(f"Whisper initialization failed: {e}", component="stt")
            return False

    def transcribe(self, audio: AudioData) -> Optional[str]:
        """
        Transcribe audio. Returns None if empty or failed.
        Sets self.last_confidence (Whisper doesn't provide per-utterance confidence,
        so we estimate from average log-prob).
        """
        if not self._loaded or self.model is None:
            logger.error("Whisper model not loaded", component="stt")
            return None

        try:
            import numpy as np

            audio_array = audio.data.astype('float32')

            # Ensure audio is 1D
            if audio_array.ndim > 1:
                audio_array = audio_array.flatten()

            # Skip very short audio (< 0.3 seconds)
            if len(audio_array) < audio.sample_rate * 0.3:
                logger.debug("Audio too short for transcription", component="stt")
                return None

            result = self.model.transcribe(
                audio_array,
                language='en',
                fp16=False,
                verbose=False
            )

            text = result['text'].strip()

            # Estimate confidence from average log probability
            segments = result.get('segments', [])
            if segments:
                avg_logprob = sum(s.get('avg_logprob', -1.0) for s in segments) / len(segments)
                # Convert log prob to 0-1 confidence (rough approximation)
                import math
                self.last_confidence = min(1.0, max(0.0, math.exp(avg_logprob)))
            else:
                self.last_confidence = 0.9  # Default high confidence

            if not text:
                return None

            logger.debug(f"Transcribed: '{text}' (confidence: {self.last_confidence:.2f})",
                         component="stt")
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}", component="stt")
            return None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def shutdown(self) -> None:
        """Release Whisper model from memory."""
        self.model = None
        self._loaded = False
        logger.debug("Whisper model unloaded", component="stt")


# ============================================================================
# VOSK IMPLEMENTATION (FALLBACK)
# ============================================================================

class VoskSTT(STTInterface):
    """Vosk speech-to-text engine (lightweight fallback)."""

    def __init__(self):
        self.model = None
        self.recognizer = None
        self._loaded = False

    def initialize(self, model: str = "vosk-model-small-en-us-0.15") -> bool:
        """
        Load Vosk model. Must be downloaded separately.
        Default model is ~40MB.
        """
        try:
            from vosk import Model, KaldiRecognizer

            model_path = f"models/vosk/{model}"
            logger.info(f"Loading Vosk model: {model_path}", component="stt")
            self.model = Model(model_path)
            self._loaded = True
            logger.info("Vosk model loaded successfully", component="stt")
            return True

        except ImportError:
            logger.warning("vosk not installed. Vosk fallback unavailable.",
                           component="stt")
            return False
        except Exception as e:
            logger.warning(f"Vosk initialization failed: {e}", component="stt")
            return False

    def transcribe(self, audio: AudioData) -> Optional[str]:
        """Transcribe audio using Vosk."""
        if not self._loaded or self.model is None:
            return None

        try:
            import json
            from vosk import KaldiRecognizer
            import numpy as np

            recognizer = KaldiRecognizer(self.model, audio.sample_rate)

            # Convert float32 to int16 for Vosk
            audio_int16 = (audio.data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            # Feed audio in chunks
            chunk_size = 4000
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                recognizer.AcceptWaveform(chunk)

            result = json.loads(recognizer.FinalResult())
            text = result.get('text', '').strip()

            if not text:
                return None

            logger.debug(f"Vosk transcribed: '{text}'", component="stt")
            return text

        except Exception as e:
            logger.error(f"Vosk transcription failed: {e}", component="stt")
            return None

    def shutdown(self) -> None:
        """Release Vosk model."""
        self.model = None
        self.recognizer = None
        self._loaded = False
        logger.debug("Vosk model unloaded", component="stt")
