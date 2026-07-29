import time
import logging
from threading import RLock
from typing import Dict, Tuple
from campus_helpdesk.domain.memory.conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class SessionManager:
    """Thread-safe session lifecycle manager for user active states and timeout cleanup."""

    def __init__(self, ttl_seconds: int = 7200, max_history_turns: int = 3):
        self.ttl_seconds = ttl_seconds
        self.max_history_turns = max_history_turns
        # Maps session_id -> (ConversationMemory, last_activity_timestamp)
        self.sessions: Dict[str, Tuple[ConversationMemory, float]] = {}
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
                memory = ConversationMemory(max_history_turns=self.max_history_turns)
                self.sessions[session_id] = (memory, now)
                logger.info(f"Initialized new session ID: {session_id}")
            return memory

    def record_activity(self, session_id: str):
        """Update last active stamp for an existing session."""
        with self._lock:
            if session_id in self.sessions:
                memory, _ = self.sessions[session_id]
                self.sessions[session_id] = (memory, time.time())

    def cleanup_expired_sessions(self):
        """Remove sessions that have exceeded the TTL limit."""
        with self._lock:
            now = time.time()
            expired_ids = []
            for session_id, (_, last_activity) in self.sessions.items():
                if now - last_activity > self.ttl_seconds:
                    expired_ids.append(session_id)
                    
            for session_id in expired_ids:
                del self.sessions[session_id]
                logger.info(f"Cleaned up expired session: {session_id}")
