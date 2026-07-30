"""Conversation analytics module for Campus Helpdesk AI.

Subscribes to session lifecycle events (``SessionStarted``, ``SessionEnded``)
and tracks session duration, turns per session, topic distribution, and
engagement metrics.

All state is thread-safe and persisted to :class:`MetricsStore`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from campus_helpdesk.analytics.event_bus import EventBus
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class ConversationAnalytics:
    """Tracks conversation/session-level analytics.

    Parameters
    ----------
    store : MetricsStore
        Persistence backend for session records.
    event_bus : EventBus, optional
        If provided, auto-subscribes to session events.
    """

    EVENT_SESSION_STARTED = "SessionStarted"
    EVENT_SESSION_ENDED = "SessionEnded"
    EVENT_TURN_COMPLETED = "TurnCompleted"

    def __init__(
        self,
        store: "MetricsStore",
        event_bus: Optional["EventBus"] = None,
    ) -> None:
        self._store = store
        self._lock = threading.Lock()

        # Active session tracking: session_id -> {start_time, turns, topics}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

        # Aggregate counters
        self._total_sessions: int = 0
        self._total_turns: int = 0
        self._session_durations: list[float] = []
        self._turns_per_session: list[int] = []
        self._topic_counts: Dict[str, int] = defaultdict(int)

        # Bounded history
        self._max_history = 500

        if event_bus is not None:
            self._subscribe(event_bus)

    def _subscribe(self, bus: "EventBus") -> None:
        bus.subscribe(self.EVENT_SESSION_STARTED, self.handle_session_started)
        bus.subscribe(self.EVENT_SESSION_ENDED, self.handle_session_ended)
        bus.subscribe(self.EVENT_TURN_COMPLETED, self.handle_turn_completed)
        logger.debug("ConversationAnalytics subscribed to EventBus.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_session_started(self, payload: Dict[str, Any]) -> None:
        """Handle ``SessionStarted`` — register a new active session."""
        try:
            session_id = payload.get("session_id") or payload.get("trace_id", "")
            with self._lock:
                self._active_sessions[session_id] = {
                    "start_time": time.monotonic(),
                    "turns": 0,
                    "topics": [],
                }
                self._total_sessions += 1

            # Persist session start
            self._store.insert_session(session_id)
            logger.debug("SessionStarted: %s", session_id)
        except Exception:
            logger.exception("Error handling SessionStarted event.")

    def handle_session_ended(self, payload: Dict[str, Any]) -> None:
        """Handle ``SessionEnded`` — compute duration and persist."""
        try:
            session_id = payload.get("session_id") or payload.get("trace_id", "")

            with self._lock:
                session_data = self._active_sessions.pop(session_id, None)

            if session_data is not None:
                duration = time.monotonic() - session_data["start_time"]
                turns = session_data["turns"]

                with self._lock:
                    self._session_durations.append(duration)
                    if len(self._session_durations) > self._max_history:
                        self._session_durations.pop(0)
                    self._turns_per_session.append(turns)
                    if len(self._turns_per_session) > self._max_history:
                        self._turns_per_session.pop(0)

                # Persist session end
                self._store.update_session_end(session_id, turns_increment=0)

            logger.debug("SessionEnded: %s", session_id)
        except Exception:
            logger.exception("Error handling SessionEnded event.")

    def handle_turn_completed(self, payload: Dict[str, Any]) -> None:
        """Handle ``TurnCompleted`` — increment turn count for the session."""
        try:
            session_id = payload.get("session_id") or payload.get("trace_id", "")
            meta = payload.get("metadata", {})
            topic = meta.get("topic", "general")

            with self._lock:
                self._total_turns += 1
                self._topic_counts[topic] += 1
                if session_id in self._active_sessions:
                    self._active_sessions[session_id]["turns"] += 1
                    self._active_sessions[session_id]["topics"].append(topic)

            # Persist turn increment
            self._store.update_session_end(session_id, turns_increment=1)

            logger.debug("TurnCompleted: session=%s topic=%s", session_id, topic)
        except Exception:
            logger.exception("Error handling TurnCompleted event.")

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current conversation-level aggregate statistics."""
        with self._lock:
            avg_duration = (
                sum(self._session_durations) / len(self._session_durations)
                if self._session_durations
                else 0.0
            )
            avg_turns = (
                sum(self._turns_per_session) / len(self._turns_per_session)
                if self._turns_per_session
                else 0.0
            )
            top_topics = sorted(
                self._topic_counts.items(), key=lambda x: x[1], reverse=True
            )[:15]

            return {
                "total_sessions": self._total_sessions,
                "total_turns": self._total_turns,
                "active_sessions": len(self._active_sessions),
                "avg_session_duration_sec": round(avg_duration, 2),
                "avg_turns_per_session": round(avg_turns, 2),
                "topic_distribution": dict(top_topics),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            }

    def reset(self) -> None:
        """Reset all in-memory state (does not clear DB)."""
        with self._lock:
            self._active_sessions.clear()
            self._total_sessions = 0
            self._total_turns = 0
            self._session_durations.clear()
            self._turns_per_session.clear()
            self._topic_counts.clear()
