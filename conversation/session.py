# conversation/session.py
"""Session management for conversation memory.
Each chat session has a unique ID, timestamps, and a ConversationManager
that holds short‑term and long‑term memory.
"""
import uuid
from datetime import datetime
from .conversation_manager import ConversationManager

class Session:
    """Represents a single user session.

    Attributes
    ----------
    session_id: str
        Unique identifier for the session.
    start_time: datetime
        When the session was created.
    last_activity: datetime
        Timestamp of the most recent interaction.
    history: list[dict]
        List of messages ``{"role": "user"|"assistant", "content": str, "timestamp": datetime}``.
    manager: ConversationManager
        Handles memory and query rewriting.
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        now = datetime.utcnow()
        self.start_time = now
        self.last_activity = now
        self.history: list[dict] = []
        self.manager = ConversationManager(self)

    def add_message(self, role: str, content: str):
        """Append a message to the session history and update activity timestamp."""
        self.history.append({"role": role, "content": content, "timestamp": datetime.utcnow()})
        self.last_activity = datetime.utcnow()
        # Also push to short‑term memory for context‑aware components
        if role == "user":
            self.manager.short_term.add_user_turn(content)
        else:
            self.manager.short_term.add_assistant_turn(content)

    def get_history(self):
        """Return the full conversation history ordered chronologically."""
        return self.history

    def clear(self):
        """Reset the session history and short‑term memory."""
        self.history.clear()
        self.manager.short_term.clear()
        self.last_activity = datetime.utcnow()

    def export(self) -> dict:
        """Export the session to a JSON‑serialisable dictionary."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "history": [
                {"role": m["role"], "content": m["content"], "timestamp": m["timestamp"].isoformat()}
                for m in self.history
            ],
            "memory_summary": self.manager.get_summary(),
        }

    @staticmethod
    def import_data(data: dict) -> "Session":
        """Create a Session instance from exported data."""
        sess = Session(session_id=data.get("session_id"))
        sess.start_time = datetime.fromisoformat(data["start_time"])
        sess.last_activity = datetime.fromisoformat(data["last_activity"])
        for entry in data.get("history", []):
            sess.history.append({
                "role": entry["role"],
                "content": entry["content"],
                "timestamp": datetime.fromisoformat(entry["timestamp"]),
            })
        # Populate short‑term memory from history (best‑effort)
        for msg in sess.history:
            if msg["role"] == "user":
                sess.manager.short_term.add_user_turn(msg["content"], timestamp=msg["timestamp"])
            else:
                sess.manager.short_term.add_assistant_turn(msg["content"], timestamp=msg["timestamp"])
        return sess

# Simple in‑process registry for active sessions
class SessionRegistry:
    _sessions: dict[str, Session] = {}

    @classmethod
    def get_or_create(cls, session_id: str | None = None) -> Session:
        if session_id and session_id in cls._sessions:
            return cls._sessions[session_id]
        sess = Session(session_id)
        cls._sessions[sess.session_id] = sess
        return sess

    @classmethod
    def clear_all(cls):
        cls._sessions.clear()

    @classmethod
    def expire_inactive(cls, timeout_seconds: int = 1800):
        """Remove sessions that have been idle for more than *timeout_seconds*.
        This is called periodically by the benchmark runner if needed.
        """
        now = datetime.utcnow()
        to_remove = [sid for sid, s in cls._sessions.items()
                     if (now - s.last_activity).total_seconds() > timeout_seconds]
        for sid in to_remove:
            del cls._sessions[sid]
