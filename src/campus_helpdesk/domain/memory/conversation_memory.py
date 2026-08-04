from threading import RLock


class ConversationMemory:
    """Thread-safe conversation memory storing message turns with size trimming."""

    def __init__(self, max_history_turns: int = 3):
        self.max_history_turns = max_history_turns
        self.messages: list[dict[str, str]] = []
        self._lock = RLock()

    def add_message(self, role: str, content: str):
        """Append message to active history, trimming if limits are exceeded."""
        with self._lock:
            self.messages.append({"role": role, "content": content})
            # Trim message history: each turn has 2 messages (user + assistant)
            max_messages = self.max_history_turns * 2
            if len(self.messages) > max_messages:
                self.messages = self.messages[-max_messages:]

    def get_messages(self) -> list[dict[str, str]]:
        """Return a copy of the active message history."""
        with self._lock:
            return list(self.messages)

    def clear(self):
        """Reset conversation memory."""
        with self._lock:
            self.messages.clear()
