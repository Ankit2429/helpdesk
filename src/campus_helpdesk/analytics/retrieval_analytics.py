"""Retrieval analytics module for Campus Helpdesk AI.

Subscribes to ``RetrievalCompleted`` events on the analytics
:class:`EventBus` and tracks retrieval quality indicators: scores, chunk
hit distributions, cross-encoder scores, and unused document counts.

All state is thread-safe and designed for low-memory footprint on RPi.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from campus_helpdesk.analytics.event_bus import EventBus
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class RetrievalAnalytics:
    """Tracks retrieval-level analytics: scores, chunk usage, quality indicators.

    Parameters
    ----------
    store : MetricsStore
        Persistence backend.
    event_bus : EventBus, optional
        If provided, auto-subscribes to ``RetrievalCompleted``.
    max_history : int
        Maximum number of recent scores to keep in memory for running
        averages.  Defaults to ``500`` (bounded memory).
    """

    EVENT_RETRIEVAL_COMPLETED = "RetrievalCompleted"

    def __init__(
        self,
        store: MetricsStore,
        event_bus: EventBus | None = None,
        max_history: int = 500,
    ) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._max_history = max_history

        # Running score buffers (ring-buffer style)
        self._retrieval_scores: list[float] = []
        self._cross_encoder_scores: list[float] = []
        self._unused_doc_counts: list[int] = []

        # Chunk hit frequency: chunk_id -> count
        self._chunk_hits: dict[str, int] = defaultdict(int)
        self._total_retrievals: int = 0

        if event_bus is not None:
            self._subscribe(event_bus)

    def _subscribe(self, bus: EventBus) -> None:
        bus.subscribe(self.EVENT_RETRIEVAL_COMPLETED, self.handle_retrieval_completed)
        logger.debug("RetrievalAnalytics subscribed to EventBus.")

    # ------------------------------------------------------------------
    # Event handler
    # ------------------------------------------------------------------

    def handle_retrieval_completed(self, payload: dict[str, Any]) -> None:
        """Handle a ``RetrievalCompleted`` event.

        Expected payload metadata keys:
            retrieved_chunk_ids (list[str]), retrieval_score (float),
            cross_encoder_score (float), unused_docs_count (int)
        """
        try:
            meta = payload.get("metadata", {})
            retrieval_score = meta.get("retrieval_score")
            cross_encoder_score = meta.get("cross_encoder_score")
            unused_docs = meta.get("unused_docs_count", 0)
            chunk_ids = meta.get("retrieved_chunk_ids", [])

            with self._lock:
                self._total_retrievals += 1

                if retrieval_score is not None:
                    self._retrieval_scores.append(float(retrieval_score))
                    if len(self._retrieval_scores) > self._max_history:
                        self._retrieval_scores.pop(0)

                if cross_encoder_score is not None:
                    self._cross_encoder_scores.append(float(cross_encoder_score))
                    if len(self._cross_encoder_scores) > self._max_history:
                        self._cross_encoder_scores.pop(0)

                self._unused_doc_counts.append(int(unused_docs))
                if len(self._unused_doc_counts) > self._max_history:
                    self._unused_doc_counts.pop(0)

                for cid in chunk_ids:
                    self._chunk_hits[str(cid)] += 1

            # Persist to MetricsStore
            retrieval_data = {
                "query_id": payload.get("trace_id", ""),
                "retrieved_chunk_ids": chunk_ids,
                "retrieval_score": retrieval_score,
                "cross_encoder_score": cross_encoder_score,
                "unused_docs_count": unused_docs,
            }
            self._store.insert_retrieval_log(retrieval_data)

            logger.debug(
                "RetrievalCompleted: score=%.3f chunks=%d",
                retrieval_score or 0.0,
                len(chunk_ids),
            )
        except Exception:
            logger.exception("Error handling RetrievalCompleted event.")

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return current in-memory retrieval quality statistics."""
        with self._lock:
            avg_ret = (
                sum(self._retrieval_scores) / len(self._retrieval_scores)
                if self._retrieval_scores
                else 0.0
            )
            avg_ce = (
                sum(self._cross_encoder_scores) / len(self._cross_encoder_scores)
                if self._cross_encoder_scores
                else 0.0
            )
            avg_unused = (
                sum(self._unused_doc_counts) / len(self._unused_doc_counts)
                if self._unused_doc_counts
                else 0.0
            )
            top_chunks = sorted(
                self._chunk_hits.items(), key=lambda x: x[1], reverse=True
            )[:20]

            return {
                "total_retrievals": self._total_retrievals,
                "avg_retrieval_score": round(avg_ret, 4),
                "avg_cross_encoder_score": round(avg_ce, 4),
                "avg_unused_docs": round(avg_unused, 2),
                "top_chunks": dict(top_chunks),
                "score_buffer_size": len(self._retrieval_scores),
                "snapshot_time": datetime.now(UTC).isoformat(),
            }

    def reset(self) -> None:
        """Reset all in-memory state."""
        with self._lock:
            self._retrieval_scores.clear()
            self._cross_encoder_scores.clear()
            self._unused_doc_counts.clear()
            self._chunk_hits.clear()
            self._total_retrievals = 0
