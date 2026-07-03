"""
skills/manager.py - Discovers, loads, and manages all skills.
Auto-discovers skills from skills/core/ and skills/third_party/.
Parses manifest.json for capabilities and dependency isolation.

Source of truth: Implementation_plan.md §4.2, Architecture_Enhancements.md §2
"""

import importlib
import inspect
from pathlib import Path
from typing import Dict, Optional

from models import IntentType, Intent, ExecutionResult, ConversationContext
from skills.base import BaseSkill
from utils.security import validate_capabilities
from utils.logger import JarvisLogger


logger = JarvisLogger()


class SkillManager:
    """
    Discovers, loads, routes, and manages lifecycle of all skills.
    """

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self._intent_map: Dict[IntentType, str] = {}

    def discover_and_load(self, config: dict = None) -> int:
        """
        Auto-discover and load skills from skills/core/ directory.

        Returns number of skills loaded.
        """
        config = config or {}
        loaded = 0

        # Discover core skills
        core_dir = Path("skills/core")
        if core_dir.exists():
            for py_file in core_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                try:
                    module_name = f"skills.core.{py_file.stem}"
                    module = importlib.import_module(module_name)

                    # Find BaseSkill subclasses in module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                            skill_config = config.get(obj.name, {})
                            if not skill_config.get('enabled', True):
                                logger.debug(f"Skill '{obj.name}' disabled",
                                             component="skills")
                                continue

                            skill = obj(config=skill_config)
                            if skill.initialize():
                                self._register_skill(skill)
                                loaded += 1
                            else:
                                logger.warning(
                                    f"Skill '{obj.name}' failed to initialize",
                                    component="skills"
                                )
                except Exception as e:
                    logger.error(f"Failed to load {py_file.name}: {e}",
                                 component="skills")

        logger.info(f"Loaded {loaded} skills", component="skills")
        return loaded

    def _register_skill(self, skill: BaseSkill):
        """Register a skill and its intent mappings."""
        self.skills[skill.name] = skill
        for intent_type in skill.get_handled_intents():
            self._intent_map[intent_type] = skill.name
        logger.debug(f"Registered skill: {skill.name} "
                     f"({len(skill.get_handled_intents())} intents)",
                     component="skills")

    def dispatch(self, intent: Intent, context: ConversationContext) -> Optional[ExecutionResult]:
        """
        Route an intent to the appropriate skill and execute.

        Security: Enforces capability manifests before routing.
        """
        skill_name = self._intent_map.get(intent.type)
        if skill_name is None:
            return None

        skill = self.skills.get(skill_name)
        if not skill:
            return None

        # Security: Enforce Capability Manifests
        if not validate_capabilities(skill, intent):
            logger.warning(
                f"Permission denied: {skill_name} lacks capabilities for "
                f"{intent.type.value}",
                component="skills"
            )
            return ExecutionResult(
                success=False,
                message=f"Permission denied: skill '{skill_name}' lacks required capabilities."
            )

        try:
            return skill.execute(intent, context)
        except Exception as e:
            logger.error(f"Skill '{skill_name}' raised exception: {e}",
                         component="skills")
            return ExecutionResult(
                success=False,
                message=f"Skill error: {e}"
            )

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def get_all_metadata(self) -> list:
        """Get metadata for all registered skills."""
        return [skill.get_metadata().to_dict() for skill in self.skills.values()]

    def shutdown(self):
        """Shutdown all skills."""
        for skill in self.skills.values():
            try:
                skill.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {skill.name}: {e}",
                             component="skills")
        logger.debug("All skills shut down", component="skills")
