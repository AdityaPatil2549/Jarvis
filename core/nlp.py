"""
core/nlp.py - Intent parsing for JARVIS-Lite.
Implements NLPInterface ABC + RuleBasedNLP (Phase 1 MVP).

Source of truth: Backend_schema.md §3.3, Implementation_plan.md §3.6
"""

import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from models import (
    Intent, IntentType, IntentParseResult, ConversationContext, ErrorType
)
from utils.logger import JarvisLogger


logger = JarvisLogger()


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================

class NLPInterface(ABC):
    """Abstract interface for NLP intent parsing."""

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def parse_intent(self, text: str, context: ConversationContext) -> IntentParseResult:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass


# ============================================================================
# APP ALIASES
# ============================================================================

APP_ALIASES: Dict[str, str] = {
    'chrome': 'chrome', 'google chrome': 'chrome', 'browser': 'chrome',
    'firefox': 'firefox', 'mozilla': 'firefox',
    'vscode': 'vscode', 'code': 'vscode', 'visual studio code': 'vscode',
    'vs code': 'vscode',
    'terminal': 'terminal', 'cmd': 'terminal', 'command prompt': 'terminal',
    'powershell': 'terminal',
    'notepad': 'notepad', 'text editor': 'notepad',
    'explorer': 'explorer', 'file explorer': 'explorer', 'finder': 'explorer',
    'files': 'explorer',
}

STOP_WORDS = {'the', 'my', 'a', 'an', 'this', 'that', 'please', 'can', 'you',
              'could', 'would', 'i', 'want', 'to', 'me', 'it', 'for'}


# ============================================================================
# RULE-BASED NLP IMPLEMENTATION
# ============================================================================

class RuleBasedNLP(NLPInterface):
    """
    Phase 1 MVP: Rule-based intent parsing using regex patterns.
    Phase 2 will swap this for LLMNativeNLP while keeping the same interface.
    """

    def __init__(self):
        self.intent_patterns: Dict[IntentType, List[str]] = {}
        self._initialized = False
        self.confidence_floor = 0.4
        self.confidence_ceiling = 0.75

    def initialize(self) -> bool:
        """Load intent patterns."""
        self.intent_patterns = {
            IntentType.OPEN_FILE: [
                r'\b(open|show|display|view)\b.*(file|document|pdf|doc|txt)',
                r'\bopen\b.*\.\w{2,4}$',
            ],
            IntentType.OPEN_APP: [
                r'\b(open|launch|start|run)\b.*(chrome|firefox|vscode|code|terminal|notepad|explorer|browser|app)',
            ],
            IntentType.CLOSE_APP: [
                r'\b(close|quit|exit|kill|terminate)\b.*(chrome|firefox|vscode|terminal|\w+)',
            ],
            IntentType.SEARCH_FILES: [
                r'\b(find|search|locate|look for|where is)\b',
            ],
            IntentType.CREATE_FILE: [
                r'\b(create|make|new)\b.*(file|document|note|text)',
            ],
            IntentType.DELETE_FILE: [
                r'\b(delete|remove|trash)\b.*(file|document)',
            ],
            IntentType.VOLUME_CONTROL: [
                r'\bvolume\b.*(up|down|increase|decrease|higher|lower|mute)',
                r'\b(increase|decrease|raise|lower)\b.*volume',
                r'\b(mute|unmute)\b',
            ],
            IntentType.SCREENSHOT: [
                r'\b(take|capture|grab)\b.*(screenshot|screen|screen shot)',
                r'\bscreenshot\b',
            ],
            IntentType.LOCK_SCREEN: [
                r'\block\b.*(screen|computer|system|workstation)',
                r'\block screen\b',
            ],
            IntentType.SYSTEM_INFO: [
                r'\b(what is|show|how much)\b.*(cpu|memory|ram|disk|battery)',
                r'\bsystem (info|stats|status)\b',
            ],
            IntentType.HELP: [
                r'\b(help|commands|what can you do|show commands)\b',
            ],
            IntentType.EXIT: [
                r'\b(exit|quit|goodbye|bye|stop|shutdown jarvis)\b',
            ],
            IntentType.UNDO: [
                r'\b(undo|cancel that|revert|nevermind|go back)\b',
            ],
            IntentType.REPEAT: [
                r'\b(repeat|say that again|what did you say|do that again)\b',
            ],
            IntentType.MACRO: [
                r'\b(run|execute)\b.*\b(routine|macro)\b',
                r'\b(morning routine|evening routine)\b',
            ],
        }
        self._initialized = True
        logger.info("Rule-based NLP initialized", component="nlp")
        return True

    def parse_intent(self, text: str, context: ConversationContext) -> IntentParseResult:
        """
        Parse user text into an Intent.

        CRITICAL: Must check context.awaiting_clarification BEFORE
        attempting a fresh regex parse (State Machine Fix from Implementation Plan).
        """
        if not self._initialized:
            return IntentParseResult(
                intent=Intent(type=IntentType.UNKNOWN, confidence=0.0, raw_text=text),
                error="NLP not initialized"
            )

        text_clean = text.strip().lower()

        # ── Step 1: Check if we're awaiting clarification ──────────────
        if context.awaiting_clarification:
            resolved = self.resolve_clarification(text_clean, context)
            if resolved is not None:
                context.clear_clarification()
                return IntentParseResult(intent=resolved)
            # If resolution failed, clear and parse as fresh command
            context.clear_clarification()

        # ── Step 2: Match against intent patterns ──────────────────────
        best_intent: Optional[Intent] = None
        best_confidence: float = 0.0

        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_clean)
                if match:
                    # Calculate confidence based on match quality
                    match_span = match.end() - match.start()
                    text_len = max(len(text_clean), 1)
                    confidence = min(0.95, 0.6 + (match_span / text_len) * 0.35)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        params = self._extract_parameters(intent_type, text_clean, match)
                        best_intent = Intent(
                            type=intent_type,
                            confidence=confidence,
                            parameters=params,
                            raw_text=text
                        )

        # ── Step 3: Handle no match ────────────────────────────────────
        if best_intent is None:
            return IntentParseResult(
                intent=Intent(type=IntentType.UNKNOWN, confidence=0.0, raw_text=text),
                error="NOT_UNDERSTOOD"
            )

        # ── Step 4: Confidence floor check ─────────────────────────────
        if best_confidence < self.confidence_floor:
            return IntentParseResult(
                intent=Intent(type=IntentType.UNKNOWN, confidence=best_confidence,
                              raw_text=text),
                error="NOT_UNDERSTOOD"
            )

        if self.confidence_floor <= best_confidence < self.confidence_ceiling:
            return IntentParseResult(
                intent=best_intent,
                requires_clarification=True,
                below_confidence_floor=True,
                clarification_message=f"Did you mean '{best_intent.type.value.replace('_', ' ')}'?"
            )

        # ── Step 5: High confidence — return directly ──────────────────
        logger.debug(
            f"Parsed intent: {best_intent.type.value} "
            f"(confidence: {best_confidence:.2f})",
            component="nlp"
        )
        return IntentParseResult(intent=best_intent)

    def resolve_clarification(self, text: str, context: ConversationContext) -> Optional[Intent]:
        """
        Resolve clarification response.
        Tries: digit → ordinal → fuzzy match.
        """
        options = context.clarification_options
        if not options:
            return None

        # Try digit input (1, 2, 3)
        text_stripped = text.strip()
        if text_stripped.isdigit():
            idx = int(text_stripped) - 1
            if 0 <= idx < len(options):
                return self._intent_from_clarification(options[idx], context)

        # Try ordinal words
        ordinals = {'first': 0, 'second': 1, 'third': 2, 'fourth': 3, 'fifth': 4,
                     'last': len(options) - 1}
        for word, idx in ordinals.items():
            if word in text_stripped and 0 <= idx < len(options):
                return self._intent_from_clarification(options[idx], context)

        # Try "yes" / "yeah" for confidence-floor confirmation
        if text_stripped in ('yes', 'yeah', 'yep', 'correct', 'right', 'y'):
            if context.last_intent:
                return context.last_intent

        # Try fuzzy matching
        try:
            from rapidfuzz import fuzz
            best_match = None
            best_score = 0
            for option in options:
                score = fuzz.partial_ratio(text_stripped, option.lower())
                if score > best_score:
                    best_score = score
                    best_match = option
            if best_score >= 70 and best_match:
                return self._intent_from_clarification(best_match, context)
        except ImportError:
            logger.debug("rapidfuzz not available for fuzzy matching", component="nlp")

        return None

    def _intent_from_clarification(self, selected: str, context: ConversationContext) -> Optional[Intent]:
        """Create an intent from a clarification selection."""
        if context.last_intent:
            intent = Intent(
                type=context.last_intent.type,
                confidence=0.95,
                parameters={**context.last_intent.parameters, 'selected': selected},
                raw_text=selected
            )
            return intent
        return None

    def _extract_parameters(self, intent_type: IntentType, text: str,
                            match: re.Match) -> Dict:
        """Extract parameters from matched text based on intent type."""
        params: Dict = {}

        if intent_type == IntentType.OPEN_APP or intent_type == IntentType.CLOSE_APP:
            # Match against app aliases
            for alias, app_name in APP_ALIASES.items():
                if alias in text:
                    params['app_name'] = app_name
                    break

        elif intent_type == IntentType.OPEN_FILE:
            # Extract filename — everything after "open", strip stop words
            words = text.split()
            action_idx = -1
            for i, w in enumerate(words):
                if w in ('open', 'show', 'display', 'view'):
                    action_idx = i
                    break
            if action_idx >= 0:
                filename_words = [w for w in words[action_idx + 1:]
                                  if w not in STOP_WORDS]
                params['filename'] = ' '.join(filename_words)

        elif intent_type == IntentType.SEARCH_FILES:
            # Everything after the search verb
            words = text.split()
            action_idx = -1
            for i, w in enumerate(words):
                if w in ('find', 'search', 'locate', 'look', 'where'):
                    action_idx = i
                    break
            if action_idx >= 0:
                query_words = [w for w in words[action_idx + 1:]
                               if w not in STOP_WORDS and w != 'for' and w != 'is']
                params['query'] = ' '.join(query_words)

        elif intent_type == IntentType.VOLUME_CONTROL:
            if any(w in text for w in ('up', 'increase', 'higher', 'raise')):
                params['action'] = 'up'
            elif any(w in text for w in ('down', 'decrease', 'lower')):
                params['action'] = 'down'
            elif 'mute' in text:
                params['action'] = 'mute'

        elif intent_type == IntentType.CREATE_FILE:
            # Try to extract filename after "called" or "named"
            for marker in ('called', 'named'):
                if marker in text:
                    idx = text.index(marker) + len(marker)
                    filename = text[idx:].strip()
                    filename = ' '.join(w for w in filename.split()
                                        if w not in STOP_WORDS)
                    params['filename'] = filename
                    break

        elif intent_type == IntentType.DELETE_FILE:
            words = text.split()
            action_idx = -1
            for i, w in enumerate(words):
                if w in ('delete', 'remove', 'trash'):
                    action_idx = i
                    break
            if action_idx >= 0:
                filename_words = [w for w in words[action_idx + 1:]
                                  if w not in STOP_WORDS]
                params['filename'] = ' '.join(filename_words)

        elif intent_type == IntentType.MACRO:
            # Extract macro name
            for marker in ('run', 'execute'):
                if marker in text:
                    idx = text.index(marker) + len(marker)
                    macro_name = text[idx:].strip()
                    macro_name = macro_name.replace('routine', '').replace('macro', '').strip()
                    if macro_name:
                        params['macro_name'] = macro_name

        return params

    def shutdown(self) -> None:
        """Clean up NLP resources."""
        self._initialized = False
        logger.debug("NLP shut down", component="nlp")
