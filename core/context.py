"""
core/context.py - Conversation state persistence for JARVIS-Lite.
Wraps ConversationContext with file I/O and core memory (SQLite).

Source of truth: Backend_schema.md §2.1, Implementation_plan.md §3.8,
                 Architecture_Enhancements.md §3
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from models import ConversationContext, ConversationTurn
from utils.logger import JarvisLogger


logger = JarvisLogger()

CORE_MEMORY_DB = Path("core_memory.sqlite")
CONTEXT_SAVE_FILE = Path("data/session_context.json")


def get_context_summary(ctx: ConversationContext) -> str:
    """
    Return brief context for NLP disambiguation.
    Used when parsing ambiguous references like "that file" or "the previous one".
    """
    if not ctx.history:
        return ""
    last_turn = ctx.history[-1]
    return f"Last: {last_turn.role}={last_turn.content[:50]}"


def save_context(ctx: ConversationContext, filepath: Optional[str] = None):
    """Persist context to JSON file (call on shutdown if save_history=True)."""
    save_path = Path(filepath) if filepath else CONTEXT_SAVE_FILE
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(ctx.to_dict(), f, indent=2, default=str)
        logger.debug(f"Context saved to {save_path}", component="context")
    except Exception as e:
        logger.error(f"Failed to save context: {e}", component="context")


def load_context(filepath: Optional[str] = None) -> ConversationContext:
    """Restore context from previous session."""
    load_path = Path(filepath) if filepath else CONTEXT_SAVE_FILE
    ctx = ConversationContext()

    try:
        if load_path.exists():
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Restore history
            for turn_data in data.get('history', []):
                ctx.history.append(ConversationTurn(
                    role=turn_data['role'],
                    content=turn_data['content']
                ))

            # Restore variables
            ctx.variables = data.get('variables', {})

            logger.info(f"Context restored: {len(ctx.history)} turns",
                        component="context")
    except Exception as e:
        logger.warning(f"Could not load context: {e}", component="context")

    # Load core beliefs from SQLite
    _load_core_beliefs(ctx)

    return ctx


# ============================================================================
# CORE MEMORY (SQLite) — Architecture Enhancement §3
# ============================================================================

def _init_core_memory_db():
    """Create core_memory.sqlite and tables if they don't exist."""
    try:
        conn = sqlite3.connect(str(CORE_MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_beliefs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                belief TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'user'
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Could not initialize core memory DB: {e}",
                       component="context")


def _load_core_beliefs(ctx: ConversationContext):
    """Load core beliefs from SQLite into context."""
    try:
        if not CORE_MEMORY_DB.exists():
            return

        conn = sqlite3.connect(str(CORE_MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT belief FROM core_beliefs ORDER BY created_at")
        ctx.core_beliefs = [row[0] for row in cursor.fetchall()]
        conn.close()

        if ctx.core_beliefs:
            logger.debug(f"Loaded {len(ctx.core_beliefs)} core beliefs",
                         component="context")
    except Exception as e:
        logger.warning(f"Could not load core beliefs: {e}", component="context")


def commit_belief(belief: str, source: str = "user"):
    """
    Store a long-term belief in core memory.
    Example: "User prefers VSCode" or "Project directory is ~/Projects"
    """
    _init_core_memory_db()
    try:
        conn = sqlite3.connect(str(CORE_MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO core_beliefs (belief, source) VALUES (?, ?)",
            (belief, source)
        )
        conn.commit()
        conn.close()
        logger.info(f"Committed belief: '{belief}'", component="context")
    except Exception as e:
        logger.error(f"Failed to commit belief: {e}", component="context")


def retrieve_beliefs() -> list:
    """Retrieve all core beliefs."""
    try:
        if not CORE_MEMORY_DB.exists():
            return []
        conn = sqlite3.connect(str(CORE_MEMORY_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT belief FROM core_beliefs ORDER BY created_at")
        beliefs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return beliefs
    except Exception:
        return []
