"""Thread-safe Conversation Memory Store.

Stores sliding window chat message history, supports history export/import,
and provides last N message retrieval without global variables.
"""

from dataclasses import dataclass, field
import datetime
import threading
from typing import Any, Dict, List, Optional
from logger.logger import get_logger

logger = get_logger("conversation_memory")


@dataclass
class ChatMessage:
    """Dataclass representing a single chat message."""

    role: str                       # 'user' or 'assistant' or 'system'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ChatMessage to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ConversationMemory:
    """Manages in-memory thread-safe conversation message history."""

    def __init__(self, max_history_size: int = 50) -> None:
        self.max_history_size = max_history_size
        self._history: List[ChatMessage] = []
        self._lock = threading.Lock()

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Append user message to history."""
        msg = ChatMessage(role="user", content=content, metadata=metadata or {})
        with self._lock:
            self._history.append(msg)
            self._trim_history()
        logger.info(f"Appended User Message (Memory size: {len(self._history)})")
        return msg

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> ChatMessage:
        """Append assistant message to history."""
        msg = ChatMessage(role="assistant", content=content, metadata=metadata or {})
        with self._lock:
            self._history.append(msg)
            self._trim_history()
        logger.info(f"Appended Assistant Message (Memory size: {len(self._history)})")
        return msg

    def get_last_n_messages(self, n: int = 10) -> List[ChatMessage]:
        """Retrieve last N messages from memory."""
        with self._lock:
            return list(self._history[-n:])

    def get_history(self) -> List[ChatMessage]:
        """Retrieve full active history."""
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        """Clear all message history."""
        with self._lock:
            self._history.clear()
        logger.info("Conversation memory cleared.")

    def export_history(self) -> List[Dict[str, Any]]:
        """Export history to list of dictionaries."""
        with self._lock:
            return [msg.to_dict() for msg in self._history]

    def _trim_history(self) -> None:
        """Trim history to max history size limit."""
        if len(self._history) > self.max_history_size:
            self._history = self._history[-self.max_history_size:]
