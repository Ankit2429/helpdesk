"""Persistent Session Memory Store Engine.

Manages structured session state (active entities, user preferences, open topics,
message history) and persists session state to storage/sessions/{session_id}.json
across reconnects. Implements sliding window + summarization memory.
"""

from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.config import STORAGE_DIR
from conversation_manager.summarizer import ConversationSummarizer
from logger.logger import get_logger

logger = get_logger("session_store")

SESSIONS_DIR: Path = STORAGE_DIR / "sessions"


@dataclass
class SessionState:
    """Dataclass representing structured persistent session state."""

    session_id: str
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    last_active_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    active_topic: str = "General"
    active_entities: Dict[str, str] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    turn_history: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class SessionMemoryStore:
    """Manages persistent session memory files and sliding window state."""

    def __init__(
        self,
        session_id: str = "default_session",
        sessions_dir: Path = SESSIONS_DIR,
        token_budget: int = 1024,
    ) -> None:
        self.session_id = session_id
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.sessions_dir / f"{self.session_id}.json"

        self.summarizer = ConversationSummarizer(token_budget=token_budget, max_unsummarized_turns=6)
        self.state = self.load_session()

    def load_session(self) -> SessionState:
        """Load session state from disk or create new session state."""
        if self.session_file.exists():
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"Loaded existing session '{self.session_id}' with {len(data.get('turn_history', []))} turns.")
                return SessionState(**data)
            except Exception as err:
                logger.warning(f"Failed reading session file '{self.session_file}': {err}. Creating new session.")

        state = SessionState(session_id=self.session_id)
        self.save_session(state)
        return state

    def save_session(self, state: Optional[SessionState] = None) -> None:
        """Persist session state to disk."""
        target_state = state or self.state
        target_state.last_active_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(asdict(target_state), f, indent=2, ensure_ascii=False)
        except Exception as err:
            logger.error(f"Failed persisting session state to '{self.session_file}': {err}")

    def add_turn(
        self,
        question: str,
        answer: str,
        entities: Dict[str, str],
        topic: str,
        user_pref_update: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append turn to session state, update active entities/topic, and auto-summarize."""
        self.state.active_topic = topic
        if entities:
            self.state.active_entities.update(entities)
        if user_pref_update:
            self.state.user_preferences.update(user_pref_update)

        turn_record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": question,
            "answer": answer,
            "topic": topic,
            "entities": entities,
        }
        self.state.turn_history.append(turn_record)

        # Update summarizer
        self.summarizer.add_turn(question, answer, entities=entities, topic=topic)
        summary_res = self.summarizer.get_summary()
        self.state.summary = summary_res.conversation_summary

        self.save_session()

    def reset(self) -> None:
        """Clear session state and remove file from disk."""
        self.state = SessionState(session_id=self.session_id)
        self.summarizer = ConversationSummarizer()
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception as e:
                logger.error(f"Error unlinking session file: {e}")
        logger.info(f"Session '{self.session_id}' reset.")
