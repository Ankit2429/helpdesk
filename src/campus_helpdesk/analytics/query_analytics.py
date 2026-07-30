"""Query analytics module for Campus Helpdesk AI.

Subscribes to query lifecycle events on the analytics :class:`EventBus` and
tracks intent distribution, status breakdown, follow-up rate, and topic
switching.  Aggregate statistics are computed in-memory and flushed to
:class:`MetricsStore` on each event.

Thread Safety
-------------
All mutable counters are guarded by a :class:`threading.Lock`.  The module
is designed to be called from the analytics ``EventBus`` handler threads.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from campus_helpdesk.analytics.event_bus import EventBus
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class QueryAnalytics:
    """Tracks query-level analytics: intents, statuses, follow-ups, topic switches.

    Parameters
    ----------
    store : MetricsStore
        Persistence backend.
    event_bus : EventBus, optional
        If provided, the module auto-subscribes to relevant events.
    """

    # Event names this module listens to
    EVENT_QUERY_RECEIVED = "QueryReceived"
    EVENT_QUERY_COMPLETED = "QueryCompleted"
    EVENT_QUERY_FAILED = "QueryFailed"

    def __init__(
        self,
        store: "MetricsStore",
        event_bus: Optional["EventBus"] = None,
    ) -> None:
        self._store = store
        self._lock = threading.Lock()

        # In-memory counters (reset on explicit flush or read)
        self._intent_counts: Dict[str, int] = defaultdict(int)
        self._status_counts: Dict[str, int] = defaultdict(int)
        self._followup_count: int = 0
        self._topic_switch_count: int = 0
        self._total_queries: int = 0

        if event_bus is not None:
            self._subscribe(event_bus)

    # ------------------------------------------------------------------
    # EventBus wiring
    # ------------------------------------------------------------------

    def _subscribe(self, bus: "EventBus") -> None:
        """Register handlers on the analytics EventBus."""
        bus.subscribe(self.EVENT_QUERY_RECEIVED, self.handle_query_received)
        bus.subscribe(self.EVENT_QUERY_COMPLETED, self.handle_query_completed)
        bus.subscribe(self.EVENT_QUERY_FAILED, self.handle_query_failed)
        logger.debug("QueryAnalytics subscribed to EventBus.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_query_received(self, payload: Dict[str, Any]) -> None:
        """Handle a ``QueryReceived`` event.

        Expected payload keys (from :meth:`PipelineTrace.event_payload`):
            trace_id, session_id, component, event_type, metadata
            metadata.raw_query, metadata.intent, metadata.has_followup,
            metadata.topic_switched
        """
        try:
            meta = payload.get("metadata", {})
            intent = meta.get("intent", "unknown")
            has_followup = bool(meta.get("has_followup", False))
            topic_switched = bool(meta.get("topic_switched", False))

            with self._lock:
                self._total_queries += 1
                self._intent_counts[intent] += 1
                if has_followup:
                    self._followup_count += 1
                if topic_switched:
                    self._topic_switch_count += 1

            logger.debug(
                "QueryReceived: intent=%s followup=%s topic_switch=%s",
                intent,
                has_followup,
                topic_switched,
            )
        except Exception:
            logger.exception("Error handling QueryReceived event.")

    def handle_query_completed(self, payload: Dict[str, Any]) -> None:
        """Handle a ``QueryCompleted`` event and persist the query log."""
        try:
            meta = payload.get("metadata", {})
            status = meta.get("status", "success")

            with self._lock:
                self._status_counts[status] += 1

            # Persist to MetricsStore
            query_data = {
                "query_id": payload.get("trace_id", ""),
                "session_id": payload.get("session_id"),
                "raw_query": meta.get("raw_query"),
                "resolved_query": meta.get("resolved_query"),
                "intent": meta.get("intent"),
                "status": status,
                "has_followup": meta.get("has_followup", False),
                "topic_switched": meta.get("topic_switched", False),
            }
            self._store.insert_query_log(query_data)

            logger.debug("QueryCompleted: trace=%s status=%s", payload.get("trace_id"), status)
        except Exception:
            logger.exception("Error handling QueryCompleted event.")

    def handle_query_failed(self, payload: Dict[str, Any]) -> None:
        """Handle a ``QueryFailed`` event."""
        try:
            with self._lock:
                self._status_counts["failed"] += 1

            meta = payload.get("metadata", {})
            query_data = {
                "query_id": payload.get("trace_id", ""),
                "session_id": payload.get("session_id"),
                "raw_query": meta.get("raw_query"),
                "resolved_query": meta.get("resolved_query"),
                "intent": meta.get("intent"),
                "status": "failed",
                "has_followup": False,
                "topic_switched": False,
            }
            self._store.insert_query_log(query_data)

            logger.debug("QueryFailed: trace=%s", payload.get("trace_id"))
        except Exception:
            logger.exception("Error handling QueryFailed event.")

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current in-memory aggregate statistics.

        Returns
        -------
        dict
            Keys: ``total_queries``, ``intent_distribution``,
            ``status_distribution``, ``followup_rate``,
            ``topic_switch_rate``, ``snapshot_time``.
        """
        with self._lock:
            total = self._total_queries or 1  # avoid div-by-zero
            return {
                "total_queries": self._total_queries,
                "intent_distribution": dict(self._intent_counts),
                "status_distribution": dict(self._status_counts),
                "followup_rate": round(self._followup_count / total, 4),
                "topic_switch_rate": round(self._topic_switch_count / total, 4),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            }

    def reset(self) -> None:
        """Reset all in-memory counters."""
        with self._lock:
            self._intent_counts.clear()
            self._status_counts.clear()
            self._followup_count = 0
            self._topic_switch_count = 0
            self._total_queries = 0
