"""
core/model_manager.py - VRAM Orchestration for JARVIS-Lite.
Manages loading/unloading of heavy models (Whisper, Ollama)
to prevent GPU OOM on low-VRAM systems.

Source of truth: Architecture_Enhancements.md §5
"""

from typing import Optional
from utils.logger import JarvisLogger


logger = JarvisLogger()


class ModelManager:
    """
    VRAM Orchestrator — ensures only one heavy model occupies GPU at a time.

    On systems with limited VRAM (≤6GB), Whisper and Ollama cannot coexist.
    This manager explicitly evicts one before loading the other.

    States:
    - STT_READY:  Whisper loaded, Ollama unloaded
    - NLP_READY:  Ollama loaded, Whisper unloaded
    - IDLE:       Neither loaded (post-init or shutdown)
    """

    def __init__(self, stt=None, nlp=None):
        self.stt = stt
        self.nlp = nlp
        self._current_state = "IDLE"
        self._vram_managed = False  # Only manage VRAM if GPU is detected

    def initialize(self):
        """Detect GPU capabilities and decide if VRAM management is needed."""
        try:
            import torch
            if torch.cuda.is_available():
                vram_mb = torch.cuda.get_device_properties(0).total_mem / 1024**2
                self._vram_managed = vram_mb < 8192  # Manage if < 8GB VRAM
                if self._vram_managed:
                    logger.info(
                        f"VRAM management enabled ({vram_mb:.0f}MB detected)",
                        component="model_manager"
                    )
                else:
                    logger.info(
                        f"VRAM management disabled (sufficient VRAM: {vram_mb:.0f}MB)",
                        component="model_manager"
                    )
            else:
                logger.info("No GPU detected — CPU-only mode, no VRAM management",
                            component="model_manager")
                self._vram_managed = False
        except ImportError:
            logger.debug("torch not available — VRAM management disabled",
                         component="model_manager")
            self._vram_managed = False

    def prepare_for_stt(self):
        """
        Prepare for speech-to-text: ensure Whisper is loaded.
        If VRAM-managed, unload NLP/LLM first.
        """
        if not self._vram_managed:
            return

        if self._current_state == "STT_READY":
            return

        logger.debug("VRAM: Preparing for STT (evicting NLP if loaded)",
                     component="model_manager")
        # In Phase 2, this would call ollama.unload() etc.
        # For Phase 1 (rule-based NLP), this is a no-op
        self._current_state = "STT_READY"

    def prepare_for_nlp(self):
        """
        Prepare for NLP: ensure LLM is loaded (Phase 2).
        If VRAM-managed, unload Whisper first.
        """
        if not self._vram_managed:
            return

        if self._current_state == "NLP_READY":
            return

        logger.debug("VRAM: Preparing for NLP (evicting STT if loaded)",
                     component="model_manager")
        # In Phase 2, this would unload Whisper and load Ollama
        # For Phase 1 (rule-based NLP), this is a no-op
        self._current_state = "NLP_READY"

    def unload_all(self):
        """Unload all models from VRAM."""
        if not self._vram_managed:
            return

        logger.debug("VRAM: Unloading all models", component="model_manager")
        self._current_state = "IDLE"

    @property
    def current_state(self) -> str:
        return self._current_state
