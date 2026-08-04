import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MetricsStore:
    """Thread-safe SQLite store for analytics metrics.

    Tables are created on first connection.  All writes go through a single
    connection with ``check_same_thread=False`` so the background analytics
    worker can write without contention.

    The ``alerts`` and ``pipeline_traces`` tables were added in Phase 2 to
    support the :class:`AlertEngine` and :class:`PipelineTrace` modules.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        turns_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS query_logs (
        query_id TEXT PRIMARY KEY,
        session_id TEXT REFERENCES sessions(session_id),
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        raw_query TEXT,
        resolved_query TEXT,
        intent TEXT,
        status TEXT CHECK (status IN ('success','fallback','failed')),
        has_followup BOOLEAN,
        topic_switched BOOLEAN
    );
    CREATE TABLE IF NOT EXISTS retrieval_logs (
        query_id TEXT REFERENCES query_logs(query_id),
        retrieved_chunk_ids TEXT,
        retrieval_score REAL,
        cross_encoder_score REAL,
        unused_docs_count INTEGER
    );
    CREATE TABLE IF NOT EXISTS latency_logs (
        query_id TEXT REFERENCES query_logs(query_id),
        query_understanding REAL,
        retrieval REAL,
        reranking REAL,
        llm_generation REAL,
        validation REAL,
        end_to_end REAL
    );
    CREATE TABLE IF NOT EXISTS quality_logs (
        query_id TEXT REFERENCES query_logs(query_id),
        confidence_score REAL,
        hallucination_flag BOOLEAN,
        citation_coverage REAL,
        unsupported_rate REAL
    );
    CREATE TABLE IF NOT EXISTS system_metrics (
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        cpu_percent REAL,
        ram_used_mb REAL
    );
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        alert_type TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'WARNING',
        message TEXT,
        resolved BOOLEAN DEFAULT 0,
        metadata TEXT
    );
    CREATE TABLE IF NOT EXISTS pipeline_traces (
        trace_id TEXT NOT NULL,
        session_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        component TEXT,
        event_type TEXT,
        latency_ms REAL,
        metadata TEXT
    );
    """

    # Tables that have a ``timestamp`` column eligible for pruning.
    _PRUNABLE_TABLES = (
        "sessions",
        "query_logs",
        "system_metrics",
        "alerts",
        "pipeline_traces",
    )

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(self.SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    # -----------------------------------------------------------------
    # Generic execute helpers
    # -----------------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def executemany(self, sql: str, seq_of_params: Any) -> None:
        with self._lock:
            self._conn.executemany(sql, seq_of_params)
            self._conn.commit()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a read query and return all rows."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute a read query and return the first row."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur.fetchone()

    # -----------------------------------------------------------------
    # Insert helpers
    # -----------------------------------------------------------------

    def insert_session(self, session_id: str, start_time: datetime | None = None) -> None:
        start_time = start_time or datetime.now(UTC)
        self.execute(
            "INSERT OR IGNORE INTO sessions (session_id, start_time) VALUES (?, ?)",
            (session_id, start_time.strftime("%Y-%m-%d %H:%M:%S")),
        )

    def update_session_end(
        self,
        session_id: str,
        end_time: datetime | None = None,
        turns_increment: int = 0,
    ) -> None:
        end_time = end_time or datetime.now(UTC)
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET end_time = ?, turns_count = turns_count + ? "
                "WHERE session_id = ?",
                (end_time.strftime("%Y-%m-%d %H:%M:%S"), turns_increment, session_id),
            )
            self._conn.commit()

    def insert_query_log(self, data: dict) -> None:
        sql = """
        INSERT OR IGNORE INTO query_logs (
            query_id, session_id, raw_query, resolved_query, intent, status,
            has_followup, topic_switched
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["query_id"],
            data.get("session_id"),
            data.get("raw_query"),
            data.get("resolved_query"),
            data.get("intent"),
            data.get("status"),
            int(bool(data.get("has_followup"))),
            int(bool(data.get("topic_switched"))),
        )
        self.execute(sql, params)

    def insert_retrieval_log(self, data: dict) -> None:
        sql = """
        INSERT INTO retrieval_logs (
            query_id, retrieved_chunk_ids, retrieval_score,
            cross_encoder_score, unused_docs_count
        ) VALUES (?, ?, ?, ?, ?)
        """
        params = (
            data["query_id"],
            json.dumps(data.get("retrieved_chunk_ids", [])),
            data.get("retrieval_score"),
            data.get("cross_encoder_score"),
            data.get("unused_docs_count"),
        )
        self.execute(sql, params)

    def insert_latency_log(self, data: dict) -> None:
        sql = """
        INSERT INTO latency_logs (
            query_id, query_understanding, retrieval, reranking,
            llm_generation, validation, end_to_end
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data["query_id"],
            data.get("query_understanding"),
            data.get("retrieval"),
            data.get("reranking"),
            data.get("llm_generation"),
            data.get("validation"),
            data.get("end_to_end"),
        )
        self.execute(sql, params)

    def insert_quality_log(self, data: dict) -> None:
        sql = """
        INSERT INTO quality_logs (
            query_id, confidence_score, hallucination_flag,
            citation_coverage, unsupported_rate
        ) VALUES (?, ?, ?, ?, ?)
        """
        params = (
            data["query_id"],
            data.get("confidence_score"),
            int(bool(data.get("hallucination_flag"))),
            data.get("citation_coverage"),
            data.get("unsupported_rate"),
        )
        self.execute(sql, params)

    def insert_system_metric(self, cpu_percent: float, ram_used_mb: float) -> None:
        self.execute(
            "INSERT INTO system_metrics (cpu_percent, ram_used_mb) VALUES (?, ?)",
            (cpu_percent, ram_used_mb),
        )

    def insert_pipeline_trace(self, data: dict) -> None:
        """Insert a pipeline trace record."""
        sql = """
        INSERT INTO pipeline_traces (
            trace_id, session_id, component, event_type, latency_ms, metadata
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            data["trace_id"],
            data.get("session_id"),
            data.get("component"),
            data.get("event_type"),
            data.get("latency_ms"),
            json.dumps(data.get("metadata", {})),
        )
        self.execute(sql, params)

    # -----------------------------------------------------------------
    # Query helpers (used by DashboardGenerator / ReportGenerator)
    # -----------------------------------------------------------------

    def get_query_stats(self, since: str | None = None) -> dict[str, Any]:
        """Return aggregate query statistics.

        Parameters
        ----------
        since : str, optional
            ISO timestamp cutoff.  If ``None``, returns all-time stats.
        """
        where = "WHERE timestamp >= ?" if since else ""
        params: tuple = (since,) if since else ()

        total_row = self.fetchone(
            f"SELECT COUNT(*) as cnt FROM query_logs {where}", params
        )
        total = total_row["cnt"] if total_row else 0

        status_rows = self.fetchall(
            f"SELECT status, COUNT(*) as cnt FROM query_logs {where} GROUP BY status",
            params,
        )
        status_dist = {row["status"]: row["cnt"] for row in status_rows}

        return {
            "total_queries": total,
            "status_distribution": status_dist,
            "success_rate": round(status_dist.get("success", 0) / max(total, 1), 4),
        }

    def get_latency_percentiles(
        self, since: str | None = None
    ) -> dict[str, float]:
        """Return latency percentiles (P50, P90, P99, avg)."""
        where = (
            "WHERE q.timestamp >= ? AND l.end_to_end IS NOT NULL"
            if since
            else "WHERE l.end_to_end IS NOT NULL"
        )
        params: tuple = (since,) if since else ()

        rows = self.fetchall(
            f"SELECT l.end_to_end FROM latency_logs l "
            f"JOIN query_logs q ON l.query_id = q.query_id "
            f"{where} ORDER BY l.end_to_end",
            params,
        )
        if not rows:
            return {"p50_ms": 0.0, "p90_ms": 0.0, "p99_ms": 0.0, "avg_ms": 0.0}

        values = [float(r["end_to_end"]) for r in rows]
        n = len(values)
        return {
            "p50_ms": round(values[int(n * 0.5)], 2),
            "p90_ms": round(values[int(n * 0.9)], 2),
            "p99_ms": round(values[min(int(n * 0.99), n - 1)], 2),
            "avg_ms": round(sum(values) / n, 2),
            "sample_count": n,
        }

    def get_alerts(
        self, since: str | None = None, unresolved_only: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch alerts, optionally filtered by time and resolution status."""
        conditions: list[str] = []
        params: list[Any] = []
        if since:
            conditions.append("timestamp >= ?")
            params.append(since)
        if unresolved_only:
            conditions.append("resolved = 0")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = self.fetchall(
            f"SELECT * FROM alerts {where} ORDER BY timestamp DESC",
            tuple(params),
        )
        return [dict(row) for row in rows]

    # -----------------------------------------------------------------
    # Pruning
    # -----------------------------------------------------------------

    def prune_old(self, retention_days: int) -> None:
        """Delete records older than *retention_days* from prunable tables.

        Tables without a ``timestamp`` column (``retrieval_logs``,
        ``latency_logs``, ``quality_logs``) are pruned via a JOIN on
        ``query_logs``.
        """
        cutoff = (
            datetime.now(UTC) - timedelta(days=retention_days)
        ).strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            cur = self._conn.cursor()

            # Direct timestamp tables
            for table in self._PRUNABLE_TABLES:
                try:
                    cur.execute(
                        f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,)
                    )
                except sqlite3.OperationalError:
                    # Table may not exist yet — skip gracefully.
                    pass

            # Dependent tables (no timestamp column) — prune via query_logs
            for dep_table in ("retrieval_logs", "latency_logs", "quality_logs"):
                try:
                    cur.execute(
                        f"DELETE FROM {dep_table} WHERE query_id IN "
                        f"(SELECT query_id FROM query_logs WHERE timestamp < ?)",
                        (cutoff,),
                    )
                except sqlite3.OperationalError:
                    pass

            self._conn.commit()

            # Reclaim space — skip for in-memory databases
            try:
                if str(self.db_path) != ":memory:" and self.db_path.exists():
                    cur.execute("VACUUM")
                    self._conn.commit()
            except Exception:
                logger.debug("VACUUM skipped.")
