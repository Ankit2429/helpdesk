"""Dashboard data generator for Campus Helpdesk AI.

Queries :class:`MetricsStore` and in-memory analytics modules to produce
structured JSON payloads consumed by the Tkinter dashboard view or a future
web UI.

The generator is stateless — each call re-queries the store so the dashboard
always reflects current data.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generates structured dashboard payloads from MetricsStore data.

    Parameters
    ----------
    store : MetricsStore
        The SQLite persistence backend to query.
    """

    def __init__(self, store: "MetricsStore") -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Generate a complete dashboard payload.

        Parameters
        ----------
        time_window_hours : int
            Lookback window for aggregate queries.

        Returns
        -------
        dict
            Keys: ``summary``, ``latency``, ``quality``, ``system_health``,
            ``recent_queries``, ``generated_at``.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        # Use strftime to match SQLite CURRENT_TIMESTAMP format (no tz, space sep)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "summary": self._get_summary(cutoff_str),
            "latency": self._get_latency_stats(cutoff_str),
            "quality": self._get_quality_stats(cutoff_str),
            "system_health": self._get_system_health(cutoff_str),
            "recent_queries": self._get_recent_queries(limit=20),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_window_hours": time_window_hours,
        }

    # ------------------------------------------------------------------
    # Private query helpers
    # ------------------------------------------------------------------

    def _query(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a read query against the store's connection."""
        try:
            with self._store._lock:
                cursor = self._store._conn.cursor()
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception:
            logger.exception("Dashboard query failed: %s", sql[:80])
            return []

    def _query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def _get_summary(self, cutoff: str) -> Dict[str, Any]:
        """Overall query volume and status breakdown."""
        total_row = self._query_one(
            "SELECT COUNT(*) as cnt FROM query_logs WHERE timestamp >= ?",
            (cutoff,),
        )
        total = total_row["cnt"] if total_row else 0

        status_rows = self._query(
            "SELECT status, COUNT(*) as cnt FROM query_logs "
            "WHERE timestamp >= ? GROUP BY status",
            (cutoff,),
        )
        status_dist = {row["status"]: row["cnt"] for row in status_rows}

        session_row = self._query_one(
            "SELECT COUNT(*) as cnt FROM sessions WHERE start_time >= ?",
            (cutoff,),
        )
        sessions = session_row["cnt"] if session_row else 0

        return {
            "total_queries": total,
            "total_sessions": sessions,
            "status_distribution": status_dist,
            "success_rate": round(
                status_dist.get("success", 0) / max(total, 1), 4
            ),
        }

    def _get_latency_stats(self, cutoff: str) -> Dict[str, Any]:
        """Latency percentiles and averages."""
        rows = self._query(
            "SELECT end_to_end FROM latency_logs l "
            "JOIN query_logs q ON l.query_id = q.query_id "
            "WHERE q.timestamp >= ? AND l.end_to_end IS NOT NULL "
            "ORDER BY l.end_to_end",
            (cutoff,),
        )
        if not rows:
            return {
                "p50_ms": 0.0,
                "p90_ms": 0.0,
                "p99_ms": 0.0,
                "avg_ms": 0.0,
                "sample_count": 0,
            }

        values = [float(r["end_to_end"]) for r in rows]
        n = len(values)

        return {
            "p50_ms": round(values[int(n * 0.5)], 2),
            "p90_ms": round(values[int(n * 0.9)], 2),
            "p99_ms": round(values[min(int(n * 0.99), n - 1)], 2),
            "avg_ms": round(sum(values) / n, 2),
            "sample_count": n,
        }

    def _get_quality_stats(self, cutoff: str) -> Dict[str, Any]:
        """Quality metric averages."""
        row = self._query_one(
            "SELECT "
            "  AVG(confidence_score) as avg_confidence, "
            "  AVG(citation_coverage) as avg_citation, "
            "  AVG(unsupported_rate) as avg_unsupported, "
            "  SUM(hallucination_flag) as hallucination_count, "
            "  COUNT(*) as total "
            "FROM quality_logs ql "
            "JOIN query_logs q ON ql.query_id = q.query_id "
            "WHERE q.timestamp >= ?",
            (cutoff,),
        )
        if not row or row["total"] == 0:
            return {
                "avg_confidence": 0.0,
                "avg_citation_coverage": 0.0,
                "avg_unsupported_rate": 0.0,
                "hallucination_rate": 0.0,
                "sample_count": 0,
            }

        total = row["total"]
        return {
            "avg_confidence": round(float(row["avg_confidence"] or 0), 4),
            "avg_citation_coverage": round(float(row["avg_citation"] or 0), 4),
            "avg_unsupported_rate": round(float(row["avg_unsupported"] or 0), 4),
            "hallucination_rate": round(
                float(row["hallucination_count"] or 0) / total, 4
            ),
            "sample_count": total,
        }

    def _get_system_health(self, cutoff: str) -> Dict[str, Any]:
        """Latest system resource metrics."""
        row = self._query_one(
            "SELECT cpu_percent, ram_used_mb, timestamp "
            "FROM system_metrics ORDER BY timestamp DESC LIMIT 1",
        )
        if not row:
            return {
                "cpu_percent": 0.0,
                "ram_used_mb": 0.0,
                "last_updated": None,
            }

        return {
            "cpu_percent": float(row["cpu_percent"]),
            "ram_used_mb": float(row["ram_used_mb"]),
            "last_updated": row["timestamp"],
        }

    def _get_recent_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return the most recent queries."""
        rows = self._query(
            "SELECT query_id, raw_query, intent, status, timestamp "
            "FROM query_logs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [
            {
                "query_id": row["query_id"],
                "raw_query": row["raw_query"],
                "intent": row["intent"],
                "status": row["status"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
