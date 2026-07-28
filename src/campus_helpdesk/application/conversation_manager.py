"""ConversationManager maintaining multi-turn chat history."""

import logging

from campus_helpdesk.domain.conversation import ChatMessage, ConversationSession

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-turn conversation memory, history formatting, and session resets."""

    def __init__(self, max_history_turns: int = 5) -> None:
        self.max_history_turns = max_history_turns
        self._sessions: dict[str, ConversationSession] = {}

    def get_session(self, session_id: str = "default") -> ConversationSession:
        """Get or initialize a conversation session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id)
        return self._sessions[session_id]

    def add_user_message(self, content: str, session_id: str = "default") -> ChatMessage:
        """Record user message turn."""
        msg = ChatMessage(role="user", content=content)
        session = self.get_session(session_id)
        session.messages.append(msg)
        self._trim_history(session)
        return msg

    def add_assistant_message(self, content: str, session_id: str = "default") -> ChatMessage:
        """Record assistant response turn."""
        msg = ChatMessage(role="assistant", content=content)
        session = self.get_session(session_id)
        session.messages.append(msg)
        self._trim_history(session)
        return msg

    def get_recent_history(self, session_id: str = "default", max_turns: int | None = None) -> list[ChatMessage]:
        """Return the most recent N message turns for prompt inclusion."""
        session = self.get_session(session_id)
        turns_limit = max_turns if max_turns is not None else self.max_history_turns
        return session.messages[-(turns_limit * 2) :] if turns_limit > 0 else []

    def format_history_prompt(self, session_id: str = "default", max_turns: int | None = None) -> str:
        """Format recent history into readable dialogue history for LLM prompt."""
        recent = self.get_recent_history(session_id, max_turns)
        if not recent:
            return ""

        lines = ["Recent Dialogue History:"]
        for msg in recent:
            role_label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")

        return "\n".join(lines)

    def reset_session(self, session_id: str = "default") -> None:
        """Clear conversation history for a given session."""
        if session_id in self._sessions:
            self._sessions[session_id].messages.clear()
            logger.info("Conversation history cleared for session: %s", session_id)

    def _trim_history(self, session: ConversationSession) -> None:
        """Keep only the latest max_history_turns * 2 messages."""
        max_messages = self.max_history_turns * 2
        if len(session.messages) > max_messages:
            session.messages = session.messages[-max_messages:]
