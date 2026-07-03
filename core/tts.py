"""
core/tts.py - Text-to-Speech for JARVIS-Lite.
Implements TTSInterface ABC + KokoroTTS (primary) + Pyttsx3TTS (fallback).

Uses: https://github.com/hexgrad/kokoro (pip install kokoro)
"""

import threading
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional

from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class TTSInterface(ABC):
    """Abstract interface for text-to-speech engines."""

    @abstractmethod
    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        pass

    @abstractmethod
    def speak(self, text: str) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        """Immediately stop ongoing speech (barge-in)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

    @property
    @abstractmethod
    def is_speaking(self) -> bool:
        pass


# ============================================================================
# KOKORO TTS IMPLEMENTATION (PRIMARY)
# ============================================================================

class KokoroTTS(TTSInterface):
    """
    Kokoro-82M text-to-speech engine — high-quality, fully local.
    Uses KPipeline from the kokoro package.

    pip install kokoro soundfile

    Architecture:
    - TTS runs in a dedicated daemon thread to avoid blocking.
    - A threading.Event (tts_interrupt_flag) enables barge-in.
    - Audio playback uses sounddevice for low-latency output.
    """

    def __init__(self):
        self.pipeline = None
        self.voice: str = "af_heart"       # Default voice
        self.lang_code: str = "a"           # 'a' = American English
        self._speaking = False
        self._lock = threading.Lock()
        self.tts_interrupt_flag = threading.Event()
        self._speech_thread: Optional[threading.Thread] = None
        self._initialized = False
        self._sample_rate = 24000  # Kokoro outputs at 24kHz

    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        """
        Initialize Kokoro TTS pipeline.

        Args:
            rate: Speech rate (not directly used by Kokoro, kept for interface compat)
            volume: Playback volume (0.0 - 1.0)
        """
        self._volume = volume

        try:
            from kokoro import KPipeline

            logger.info(
                f"Loading Kokoro TTS (voice={self.voice}, lang={self.lang_code})",
                component="tts"
            )

            self.pipeline = KPipeline(lang_code=self.lang_code)

            self._initialized = True
            logger.info(
                f"Kokoro TTS initialized (voice={self.voice})",
                component="tts"
            )
            return True

        except ImportError:
            logger.error(
                "kokoro not installed. Run: pip install kokoro soundfile",
                component="tts"
            )
            return False
        except Exception as e:
            logger.error(f"Kokoro TTS initialization failed: {e}",
                         component="tts")
            return False

    def speak(self, text: str) -> None:
        """
        Speak text in a background daemon thread.
        Supports barge-in: set tts_interrupt_flag to halt speech.
        """
        if not self._initialized or not self.pipeline:
            logger.warning("TTS not initialized, skipping speech",
                           component="tts")
            return

        # Clear any previous interrupt
        self.tts_interrupt_flag.clear()

        # Run in daemon thread
        self._speech_thread = threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True
        )
        self._speech_thread.start()

    def _speak_worker(self, text: str):
        """
        Worker thread for Kokoro TTS.

        Kokoro yields audio segments via a generator.
        We play each segment sequentially, checking the interrupt flag
        between segments for barge-in support (<100ms halt).
        """
        try:
            with self._lock:
                self._speaking = True

            import sounddevice as sd

            # Generate speech segments
            generator = self.pipeline(text, voice=self.voice)

            for _graphemes, _phonemes, audio_array in generator:
                # Check interrupt before each segment
                if self.tts_interrupt_flag.is_set():
                    logger.debug("TTS interrupted (barge-in)", component="tts")
                    break

                if audio_array is None or len(audio_array) == 0:
                    continue

                # Apply volume
                audio_out = audio_array * self._volume

                # Play audio segment synchronously (blocks until done)
                sd.play(audio_out, samplerate=self._sample_rate)
                sd.wait()

        except ImportError as e:
            logger.error(f"TTS playback dependency missing: {e}", component="tts")
        except Exception as e:
            logger.error(f"TTS error: {e}", component="tts")
        finally:
            with self._lock:
                self._speaking = False

    def stop(self) -> None:
        """Immediately stop ongoing speech (barge-in)."""
        self.tts_interrupt_flag.set()
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
        with self._lock:
            self._speaking = False
        logger.debug("TTS stopped (barge-in)", component="tts")

    @property
    def is_speaking(self) -> bool:
        """Return True if currently speaking."""
        with self._lock:
            return self._speaking

    def shutdown(self) -> None:
        """Clean up TTS resources."""
        self.stop()
        self.pipeline = None
        self._initialized = False
        logger.debug("Kokoro TTS shut down", component="tts")


# ============================================================================
# PYTTSX3 FALLBACK
# ============================================================================

class Pyttsx3TTS(TTSInterface):
    """
    pyttsx3 TTS fallback — uses system SAPI5/espeak.
    Used when Kokoro is not available or fails to initialize.
    """

    def __init__(self):
        self.engine = None
        self._speaking = False
        self._lock = threading.Lock()
        self.tts_interrupt_flag = threading.Event()
        self._speech_thread: Optional[threading.Thread] = None
        self._initialized = False

    def initialize(self, rate: int = 175, volume: float = 0.9) -> bool:
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            self._select_voice()
            self._initialized = True
            logger.info(f"pyttsx3 TTS initialized (rate={rate})",
                        component="tts")
            return True

        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3",
                         component="tts")
            return False
        except Exception as e:
            logger.error(f"pyttsx3 initialization failed: {e}", component="tts")
            return False

    def _select_voice(self):
        """Select best available voice."""
        if not self.engine:
            return
        voices = self.engine.getProperty('voices')
        preferred = ['david', 'alex', 'daniel', 'mark', 'zira']
        for voice in voices:
            if any(pref in voice.name.lower() for pref in preferred):
                self.engine.setProperty('voice', voice.id)
                return
        if voices:
            self.engine.setProperty('voice', voices[0].id)

    def speak(self, text: str) -> None:
        if not self._initialized or not self.engine:
            return
        self.tts_interrupt_flag.clear()
        self._speech_thread = threading.Thread(
            target=self._speak_worker, args=(text,), daemon=True
        )
        self._speech_thread.start()

    def _speak_worker(self, text: str):
        try:
            import re
            with self._lock:
                self._speaking = True

            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if self.tts_interrupt_flag.is_set():
                    break
                sentence = sentence.strip()
                if not sentence:
                    continue
                self.engine.say(sentence)
                self.engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}", component="tts")
        finally:
            with self._lock:
                self._speaking = False

    def stop(self) -> None:
        self.tts_interrupt_flag.set()
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
        with self._lock:
            self._speaking = False

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking

    def shutdown(self) -> None:
        self.stop()
        self._initialized = False
