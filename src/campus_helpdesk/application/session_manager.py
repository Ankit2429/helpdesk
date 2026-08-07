import logging
import time
from threading import RLock

from campus_helpdesk.domain.memory.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)


class SessionManager:
    """Thread-safe session lifecycle manager for user active states and timeout cleanup."""

    def __init__(
        self,
        ttl_seconds: int | None = None,
        max_history_turns: int | None = None,
        summary_trigger_turns: int | None = None,
        max_context_tokens: int | None = None,
    ):
        try:
            from campus_helpdesk.config.settings import get_settings
            settings = get_settings()
            self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.memory_session_ttl_seconds
            self.max_history_turns = max_history_turns if max_history_turns is not None else settings.memory_max_history_turns
            self.summary_trigger_turns = summary_trigger_turns if summary_trigger_turns is not None else settings.memory_summary_trigger_turns
            self.max_context_tokens = max_context_tokens if max_context_tokens is not None else settings.memory_max_context_tokens
        except Exception:
            self.ttl_seconds = ttl_seconds if ttl_seconds is not None else 300
            self.max_history_turns = max_history_turns if max_history_turns is not None else 5
            self.summary_trigger_turns = summary_trigger_turns if summary_trigger_turns is not None else 5
            self.max_context_tokens = max_context_tokens if max_context_tokens is not None else 2048

        # Maps session_id -> (ConversationMemory, last_activity_timestamp)
        self.sessions: dict[str, tuple[ConversationMemory, float]] = {}
        self._lock = RLock()

    def get_or_create_session(self, session_id: str) -> ConversationMemory:
        """Fetch existing session or initialize a new memory block, updating last active stamp."""
        with self._lock:
            # Periodically trigger cleanup on session requests
            self.cleanup_expired_sessions()

            now = time.time()
            if session_id in self.sessions:
                memory, _ = self.sessions[session_id]
                self.sessions[session_id] = (memory, now)
                logger.debug(f"Retrieved active session: {session_id}")
            else:
                memory = ConversationMemory(
                    max_history_turns=self.max_history_turns,
                    summary_trigger_turns=self.summary_trigger_turns,
                    max_context_tokens=self.max_context_tokens,
                )
                self.sessions[session_id] = (memory, now)
                logger.info(f"Initialized new session ID: {session_id}")
            return memory

    def record_activity(self, session_id: str):
        """Update last active stamp for an existing session."""
        with self._lock:
            if session_id in self.sessions:
                memory, _ = self.sessions[session_id]
                self.sessions[session_id] = (memory, time.time())

    def clear_session(self, session_id: str):
        """Explicitly clear memory and delete a specific session."""
        with self._lock:
            if session_id in self.sessions:
                memory, _ = self.sessions[session_id]
                memory.clear()
                del self.sessions[session_id]
                logger.info(f"Explicitly cleared session ID: {session_id}")

    def clear_all_sessions(self):
        """Clear memory across all active sessions."""
        with self._lock:
            for session_id, (memory, _) in self.sessions.items():
                memory.clear()
            self.sessions.clear()
            logger.info("Cleared all active sessions.")

    def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded the TTL limit."""
        with self._lock:
            now = time.time()
            expired_ids = []
            for session_id, (_, last_activity) in self.sessions.items():
                if now - last_activity > self.ttl_seconds:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                if session_id in self.sessions:
                    memory, _ = self.sessions[session_id]
                    memory.clear()
                    del self.sessions[session_id]
                    logger.info(f"Cleaned up expired session: {session_id}")
