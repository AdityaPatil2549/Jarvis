"""
core/audio.py - Audio capture and playback for JARVIS-Lite.
Implements AudioInterface ABC + SoundDeviceAudio.

Source of truth: Backend_schema.md §3.1, Implementation_plan.md §3.4
"""

import time
import threading
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Callable

from models import AudioConfig, AudioData, AudioFormat
from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class AudioInterface(ABC):
    """Abstract interface for audio capture."""

    @abstractmethod
    def initialize(self, config: AudioConfig) -> bool:
        """Initialize audio system. Return True if ready."""
        pass

    @abstractmethod
    def start_recording(self) -> None:
        """Begin capturing audio from microphone."""
        pass

    @abstractmethod
    def stop_recording(self) -> AudioData:
        """Stop capturing and return audio data."""
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        pass

    @abstractmethod
    def get_audio_level(self) -> float:
        """Return current audio level (0.0 - 1.0)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up audio resources."""
        pass


# ============================================================================
# SOUNDDEVICE IMPLEMENTATION
# ============================================================================

class SoundDeviceAudio(AudioInterface):
    """Audio capture using sounddevice library."""

    def __init__(self):
        self.config: Optional[AudioConfig] = None
        self._recording = False
        self._audio_buffer: list = []
        self._current_level: float = 0.0
        self._stream = None
        self._record_start_time: float = 0.0
        self._lock = threading.Lock()

    def initialize(self, config: Optional[AudioConfig] = None) -> bool:
        """Initialize audio system with SoundDevice."""
        self.config = config or AudioConfig()

        try:
            import sounddevice as sd

            # Verify a microphone is available
            devices = sd.query_devices()
            input_device = sd.default.device[0]

            if input_device is None or input_device < 0:
                logger.error("No microphone found. Check audio settings.",
                             component="audio")
                return False

            device_info = sd.query_devices(input_device)
            logger.info(f"Audio initialized: {device_info['name']}",
                        component="audio")
            return True

        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice",
                         component="audio")
            return False
        except Exception as e:
            logger.error(f"Audio initialization failed: {e}", component="audio")
            return False

    def start_recording(self) -> None:
        """Begin capturing audio from microphone."""
        import sounddevice as sd

        with self._lock:
            self._audio_buffer = []
            self._recording = True
            self._record_start_time = time.time()

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio callback status: {status}",
                               component="audio")
            with self._lock:
                if self._recording:
                    self._audio_buffer.append(indata.copy())
                    # Update current audio level
                    self._current_level = float(np.sqrt(np.mean(indata ** 2)))

        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype='float32',
            blocksize=self.config.chunk_size,
            callback=audio_callback,
            device=self.config.device_index
        )
        self._stream.start()
        logger.debug("Recording started", component="audio")

    def stop_recording(self) -> AudioData:
        """Stop capturing and return audio data."""
        with self._lock:
            self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        # Concatenate audio buffer
        with self._lock:
            if self._audio_buffer:
                audio_array = np.concatenate(self._audio_buffer, axis=0)
            else:
                audio_array = np.array([], dtype='float32')

        duration = time.time() - self._record_start_time
        logger.debug(f"Recording stopped: {duration:.2f}s", component="audio")

        return AudioData(
            data=audio_array.flatten(),
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration=duration,
            format=AudioFormat.FLOAT32
        )

    def is_recording(self) -> bool:
        """Return True if currently recording."""
        with self._lock:
            return self._recording

    def get_audio_level(self) -> float:
        """Return current audio level (0.0 - 1.0)."""
        with self._lock:
            return min(1.0, self._current_level * 10)

    def get_waveform_visualization(self, audio_chunk: Optional[np.ndarray] = None) -> str:
        """
        Return ASCII waveform for UI display during recording.
        Maps audio amplitude to block characters: ▁▂▃▄▅▆▇█
        """
        levels = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        current_level = self.get_audio_level()
        level_idx = min(7, int(current_level * 8))
        return levels[level_idx] * 16

    def detect_silence(self, audio_chunk: np.ndarray, threshold: float = 0.01) -> bool:
        """Return True if audio chunk is silent (below threshold RMS)."""
        rms = float(np.sqrt(np.mean(audio_chunk ** 2)))
        return rms < threshold

    def shutdown(self) -> None:
        """Clean up audio resources."""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.debug("Audio system shut down", component="audio")
