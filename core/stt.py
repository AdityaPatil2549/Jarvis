"""
core/stt.py - Speech-to-Text for JARVIS-Lite.
Implements STTInterface ABC + FasterWhisperSTT (primary) + VoskSTT (fallback).

Uses: https://github.com/SYSTRAN/faster-whisper (pip install faster-whisper)
"""

import math
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
# FASTER-WHISPER IMPLEMENTATION (PRIMARY)
# ============================================================================

class FasterWhisperSTT(STTInterface):
    """
    SYSTRAN faster-whisper speech-to-text engine (primary).
    Uses CTranslate2 for 4x faster inference than openai-whisper.

    pip install faster-whisper
    """

    def __init__(self):
        self.model = None
        self.model_name: str = "base"
        self.last_confidence: float = 0.0
        self._loaded = False
        self._device: str = "cpu"
        self._compute_type: str = "int8"

    def initialize(self, model: str = "base") -> bool:
        """
        Load faster-whisper model.
        Model sizes: tiny, base, small, medium, large-v3
        Auto-detects GPU and selects optimal compute type.
        """
        self.model_name = model
        try:
            from faster_whisper import WhisperModel

            # Auto-detect device
            try:
                import torch
                if torch.cuda.is_available():
                    self._device = "cuda"
                    self._compute_type = "float16"
                    logger.info("GPU detected — using CUDA with float16",
                                component="stt")
                else:
                    self._device = "cpu"
                    self._compute_type = "int8"
                    logger.info("No GPU — using CPU with int8 quantization",
                                component="stt")
            except ImportError:
                self._device = "cpu"
                self._compute_type = "int8"
                logger.info("torch not found — defaulting to CPU int8",
                            component="stt")

            logger.info(
                f"Loading faster-whisper model: {model} "
                f"(device={self._device}, compute={self._compute_type})",
                component="stt"
            )

            self.model = WhisperModel(
                model,
                device=self._device,
                compute_type=self._compute_type
            )

            self._loaded = True
            logger.info(f"faster-whisper model '{model}' loaded successfully",
                        component="stt")
            return True

        except ImportError:
            logger.error(
                "faster-whisper not installed. Run: pip install faster-whisper",
                component="stt"
            )
            return False
        except Exception as e:
            logger.error(f"faster-whisper initialization failed: {e}",
                         component="stt")
            return False

    def transcribe(self, audio: AudioData) -> Optional[str]:
        """
        Transcribe audio using faster-whisper.
        Returns None if empty or failed.
        Populates self.last_confidence from segment avg_logprob.
        """
        if not self._loaded or self.model is None:
            logger.error("faster-whisper model not loaded", component="stt")
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

            # faster-whisper returns (segments_generator, info)
            segments, info = self.model.transcribe(
                audio_array,
                language='en',
                beam_size=5,
                vad_filter=True,  # Skip silence automatically
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )

            # Consume generator and collect text + confidence
            texts = []
            logprobs = []
            for segment in segments:
                texts.append(segment.text.strip())
                logprobs.append(segment.avg_logprob)

            text = ' '.join(texts).strip()

            # Estimate confidence from average log probability
            if logprobs:
                avg_logprob = sum(logprobs) / len(logprobs)
                self.last_confidence = min(1.0, max(0.0, math.exp(avg_logprob)))
            else:
                self.last_confidence = 0.0

            if not text:
                return None

            logger.debug(
                f"Transcribed: '{text}' "
                f"(confidence: {self.last_confidence:.2f}, "
                f"lang: {info.language} [{info.language_probability:.0%}])",
                component="stt"
            )
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}", component="stt")
            return None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def shutdown(self) -> None:
        """Release model from memory."""
        self.model = None
        self._loaded = False
        logger.debug("faster-whisper model unloaded", component="stt")


# ============================================================================
# VOSK IMPLEMENTATION (FALLBACK)
# ============================================================================

class VoskSTT(STTInterface):
    """Vosk speech-to-text engine (lightweight CPU-only fallback)."""

    def __init__(self):
        self.model = None
        self.recognizer = None
        self._loaded = False

    def initialize(self, model: str = "vosk-model-small-en-us-0.15") -> bool:
        """Load Vosk model from models/vosk/ directory."""
        try:
            from vosk import Model

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
            import numpy as np
            from vosk import KaldiRecognizer

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
