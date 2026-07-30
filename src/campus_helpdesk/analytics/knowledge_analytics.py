"""Knowledge analytics module for Campus Helpdesk AI.

Subscribes to ``RetrievalCompleted`` events and analyses document / chunk
access patterns to surface:

* Most and least accessed documents
* Chunk utilisation distribution
* Knowledge gap detection (frequently failing queries)
* "Unknown question" pattern collection

All state is thread-safe with bounded memory for Raspberry Pi deployment.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from campus_helpdesk.analytics.event_bus import EventBus
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class KnowledgeAnalytics:
    """Analyses knowledge-base access patterns and detects gaps.

    Parameters
    ----------
    store : MetricsStore
        Persistence backend.
    event_bus : EventBus, optional
        If provided, auto-subscribes to relevant events.
    max_unknown_questions : int
        Maximum number of unknown questions to retain.
    """

    EVENT_RETRIEVAL_COMPLETED = "RetrievalCompleted"
    EVENT_QUERY_FAILED = "QueryFailed"

    def __init__(
        self,
        store: "MetricsStore",
        event_bus: Optional["EventBus"] = None,
        max_unknown_questions: int = 200,
    ) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._max_unknown = max_unknown_questions

        # Document access frequency: source_path -> count
        self._doc_access: Dict[str, int] = defaultdict(int)
        # Chunk access frequency: chunk_id -> count
        self._chunk_access: Dict[str, int] = defaultdict(int)

        # Knowledge gaps: questions that got no useful retrieval results
        self._unknown_questions: List[Dict[str, Any]] = []
        self._total_events: int = 0

        if event_bus is not None:
            self._subscribe(event_bus)

    def _subscribe(self, bus: "EventBus") -> None:
        bus.subscribe(self.EVENT_RETRIEVAL_COMPLETED, self.handle_retrieval_completed)
        bus.subscribe(self.EVENT_QUERY_FAILED, self.handle_query_failed)
        logger.debug("KnowledgeAnalytics subscribed to EventBus.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_retrieval_completed(self, payload: Dict[str, Any]) -> None:
        """Process retrieval results to update document and chunk access stats."""
        try:
            meta = payload.get("metadata", {})
            chunk_ids = meta.get("retrieved_chunk_ids", [])
            source_docs = meta.get("source_documents", [])
            retrieval_score = meta.get("retrieval_score")
            raw_query = meta.get("raw_query", "")

            with self._lock:
                self._total_events += 1

                # Track chunk access
                for cid in chunk_ids:
                    self._chunk_access[str(cid)] += 1

                # Track document access
                for doc_path in source_docs:
                    self._doc_access[str(doc_path)] += 1

                # Detect knowledge gap: low retrieval score with no useful chunks
                if retrieval_score is not None and retrieval_score < 0.3 and raw_query:
                    self._record_unknown_question(raw_query, retrieval_score)

            logger.debug(
                "KnowledgeAnalytics: processed %d chunks from %d docs",
                len(chunk_ids),
                len(source_docs),
            )
        except Exception:
            logger.exception("Error in KnowledgeAnalytics.handle_retrieval_completed.")

    def handle_query_failed(self, payload: Dict[str, Any]) -> None:
        """Record queries that failed as potential knowledge gaps."""
        try:
            meta = payload.get("metadata", {})
            raw_query = meta.get("raw_query", "")
            if raw_query:
                with self._lock:
                    self._record_unknown_question(raw_query, score=0.0)
            logger.debug("KnowledgeAnalytics: recorded failed query.")
        except Exception:
            logger.exception("Error in KnowledgeAnalytics.handle_query_failed.")

    def _record_unknown_question(self, query: str, score: float) -> None:
        """Record an unknown question (must hold ``_lock``)."""
        entry = {
            "question": query,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._unknown_questions.append(entry)
        if len(self._unknown_questions) > self._max_unknown:
            self._unknown_questions.pop(0)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_most_accessed_documents(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Return the ``top_n`` most accessed documents."""
        with self._lock:
            sorted_docs = sorted(
                self._doc_access.items(), key=lambda x: x[1], reverse=True
            )[:top_n]
            return [{"document": doc, "access_count": count} for doc, count in sorted_docs]

    def get_least_accessed_documents(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Return the ``top_n`` least accessed documents (potential stale content)."""
        with self._lock:
            sorted_docs = sorted(
                self._doc_access.items(), key=lambda x: x[1]
            )[:top_n]
            return [{"document": doc, "access_count": count} for doc, count in sorted_docs]

    def get_unknown_questions(self) -> List[Dict[str, Any]]:
        """Return collected unknown / low-score questions."""
        with self._lock:
            return list(self._unknown_questions)

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive knowledge analytics statistics."""
        with self._lock:
            return {
                "total_events": self._total_events,
                "unique_documents_accessed": len(self._doc_access),
                "unique_chunks_accessed": len(self._chunk_access),
                "unknown_questions_count": len(self._unknown_questions),
                "top_documents": dict(
                    sorted(
                        self._doc_access.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                ),
                "top_chunks": dict(
                    sorted(
                        self._chunk_access.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:10]
                ),
                "snapshot_time": datetime.now(timezone.utc).isoformat(),
            }

    def reset(self) -> None:
        """Reset all in-memory state."""
        with self._lock:
            self._doc_access.clear()
            self._chunk_access.clear()
            self._unknown_questions.clear()
            self._total_events = 0
