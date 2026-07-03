"""
skills/base.py - Base class for all JARVIS skills.
Every skill inherits from BaseSkill and implements execute().

Source of truth: Implementation_plan.md §4.1
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from models import Intent, IntentType, ExecutionResult, ConversationContext, SkillMetadata
from utils.logger import JarvisLogger


logger = JarvisLogger()


class BaseSkill(ABC):
    """Abstract base for all JARVIS skills."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    manifest = None  # SkillManifest for third-party skills, None for core

    def __init__(self, config: dict = None):
        self.config = config or {}

    @abstractmethod
    def initialize(self) -> bool:
        """Called once when skill is loaded. Return True if ready."""
        pass

    @abstractmethod
    def get_handled_intents(self) -> List[IntentType]:
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
            functions=[it.value for it in self.get_handled_intents()]
        )
