"""
core/config_manager.py - Configuration loader for JARVIS-Lite.
Loads and validates config/settings.json and config/macros.json.

Source of truth: Implementation_plan.md §3.10
"""

import json
from pathlib import Path
from typing import Any, Optional

from models import SystemConfig
from utils.logger import JarvisLogger


logger = JarvisLogger()


class ConfigManager:
    """Loads, validates, and provides access to system configuration."""

    CONFIG_FILE = Path("config/settings.json")
    MACRO_FILE = Path("config/macros.json")

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.CONFIG_FILE = Path(config_path)
        self.config: dict = {}
        self.macros: dict = {}
        self._system_config: Optional[SystemConfig] = None

    def load_all(self) -> SystemConfig:
        """Load settings.json and macros.json, merge into SystemConfig."""
        self._load_settings()
        self._load_macros()
        self._system_config = self._build_system_config()
        logger.info("Configuration loaded successfully", component="config")
        return self._system_config

    def _load_settings(self):
        """Load settings.json."""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.debug(f"Settings loaded from {self.CONFIG_FILE}",
                             component="config")
            else:
                logger.warning(f"Config file not found: {self.CONFIG_FILE}",
                               component="config")
                self.config = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.CONFIG_FILE}: {e}",
                         component="config")
            self.config = {}

    def _load_macros(self):
        """Load macros.json."""
        try:
            if self.MACRO_FILE.exists():
                with open(self.MACRO_FILE, 'r', encoding='utf-8') as f:
                    self.macros = json.load(f)
                logger.debug(f"Macros loaded: {len(self.macros)} macros",
                             component="config")
            else:
                self.macros = {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.MACRO_FILE}: {e}",
                         component="config")
            self.macros = {}

    def _build_system_config(self) -> SystemConfig:
        """Build SystemConfig from loaded settings."""
        pipeline = self.config.get('pipeline', {})
        audio_cfg = self.config.get('audio', {})
        features = self.config.get('features', {})
        skills_cfg = self.config.get('skills', {})

        return SystemConfig(
            stt_engine=pipeline.get('stt', {}).get('engine', 'whisper'),
            stt_model=pipeline.get('stt', {}).get('model', 'base'),
            tts_engine=pipeline.get('tts', {}).get('engine', 'pyttsx3'),
            tts_rate=pipeline.get('tts', {}).get('rate', 175),
            tts_volume=pipeline.get('tts', {}).get('volume', 0.9),
            nlp_engine=pipeline.get('nlp', {}).get('engine', 'spacy'),
            nlp_model=pipeline.get('nlp', {}).get('model', 'en_core_web_sm'),
            allowed_directories=skills_cfg.get('file_operations', {}).get(
                'allowed_directories',
                ['~/Documents', '~/Desktop', '~/Downloads']
            ),
            wake_word_enabled=features.get('wake_word_enabled', False),
            save_history=features.get('save_history', True),
            verbose_logging=features.get('verbose_logging', False),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Dot-notation config access.
        Example: get('pipeline.stt.engine') → 'whisper'
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def get_macro(self, name: str) -> Optional[list]:
        """Get a macro by name. Returns list of steps or None."""
        return self.macros.get(name)

    def reload(self):
        """Re-read config files from disk."""
        logger.info("Reloading configuration", component="config")
        self.load_all()

    @property
    def system_config(self) -> SystemConfig:
        """Get SystemConfig (loads if not yet loaded)."""
        if self._system_config is None:
            self.load_all()
        return self._system_config
