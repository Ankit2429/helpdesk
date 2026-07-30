"""Central analytics orchestrator for Campus Helpdesk AI.

Wires every analytics module to the lightweight analytics :class:`EventBus`,
manages the background worker queue, and exposes façade methods for
dashboards, alerts, and reports.

Usage::

    manager = AnalyticsManager()
    manager.start()
    manager.track_turn(turn_data)
    dashboard = manager.get_dashboard()
    manager.stop()
"""

from __future__ import annotations

import logging
import queue
import threading
import uuid
from typing import Any, Dict, List, Optional

from campus_helpdesk.analytics.alert_engine import AlertEngine
from campus_helpdesk.analytics.conversation_analytics import ConversationAnalytics
from campus_helpdesk.analytics.dashboard_generator import DashboardGenerator
from campus_helpdesk.analytics.event_bus import EventBus
from campus_helpdesk.analytics.knowledge_analytics import KnowledgeAnalytics
from campus_helpdesk.analytics.metrics_store import MetricsStore
from campus_helpdesk.analytics.performance_monitor import PerformanceMonitor
from campus_helpdesk.analytics.query_analytics import QueryAnalytics
from campus_helpdesk.analytics.report_generator import ReportGenerator
from campus_helpdesk.analytics.retrieval_analytics import RetrievalAnalytics

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Central orchestrator — creates and wires all analytics subsystems.

    Parameters
    ----------
    config : dict, optional
        Override default configuration keys.  Recognised keys:

        * ``database_path`` — SQLite file location.
        * ``retention_days`` — how long to keep data.
        * ``system_monitor_interval_seconds`` — perf-monitor polling rate.
        * ``alert_thresholds`` — dict of threshold overrides.
        * ``report_output_dir`` — where reports are written.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        default_cfg: Dict[str, Any] = {
            "database_path": "data/analytics/metrics.sqlite",
            "retention_days": 30,
            "system_monitor_interval_seconds": 10,
            "alert_thresholds": {},
            "report_output_dir": "data/analytics/reports",
        }
        self.cfg = {**default_cfg, **(config or {})}

        # Core infrastructure
        self.store = MetricsStore(self.cfg["database_path"])
        self.event_bus = EventBus()

        # Background worker queue
        self._queue: queue.Queue[Optional[Dict[str, Any]]] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(
            target=self._process_queue,
            name="AnalyticsWorker",
            daemon=True,
        )

        # Performance monitor
        self.perf_monitor = PerformanceMonitor(
            self.store,
            self.cfg["system_monitor_interval_seconds"],
        )

        # Analytics modules — each subscribes to EventBus
        self.query_analytics = QueryAnalytics(self.store, self.event_bus)
        self.retrieval_analytics = RetrievalAnalytics(self.store, self.event_bus)
        self.conversation_analytics = ConversationAnalytics(self.store, self.event_bus)
        self.knowledge_analytics = KnowledgeAnalytics(self.store, self.event_bus)

        # Alert engine
        self.alert_engine = AlertEngine(
            self.store,
            self.event_bus,
            thresholds=self.cfg.get("alert_thresholds"),
        )

        # Dashboard & report generators
        self.dashboard_generator = DashboardGenerator(self.store)
        self.report_generator = ReportGenerator(
            self.store,
            output_dir=self.cfg["report_output_dir"],
            dashboard_generator=self.dashboard_generator,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background worker and performance monitor."""
        self._worker.start()
        self.perf_monitor.start()
        logger.info("AnalyticsManager started.")

    def stop(self) -> None:
        """Signal termination and wait for all threads to finish."""
        self._stop_event.set()
        self._queue.put(None)  # unblock the worker
        self._worker.join(timeout=5)
        self.perf_monitor.stop()
        logger.info("AnalyticsManager stopped.")

    # ------------------------------------------------------------------
    # Event publishing (used by backend components)
    # ------------------------------------------------------------------

    def publish_event(self, event_name: str, payload: Any = None) -> None:
        """Publish an event on the analytics EventBus.

        Backend components should call this method rather than reaching
        into ``self.event_bus`` directly.
        """
        self.event_bus.publish(event_name, payload)

    # ------------------------------------------------------------------
    # Turn tracking (legacy compat + queue-based persistence)
    # ------------------------------------------------------------------

    def track_turn(self, turn_data: Dict[str, Any]) -> None:
        """Enqueue a turn's metrics for asynchronous persistence.

        Expected keys in ``turn_data`` (all optional):
            session_id, query_id, raw_query, resolved_query, intent, status,
            has_followup, topic_switched, latencies (dict), quality (dict),
            retrieval (dict)
        """
        turn_data.setdefault("session_id", str(uuid.uuid4()))
        turn_data.setdefault("query_id", str(uuid.uuid4()))
        self._queue.put(turn_data)

    def _process_queue(self) -> None:
        """Background loop consuming queued turn data."""
        while not self._stop_event.is_set():
            item = self._queue.get()
            if item is None:
                break
            try:
                self._persist(item)
            except Exception:
                logger.exception("Failed to persist analytics turn.")
            finally:
                self._queue.task_done()

    def _persist(self, data: Dict[str, Any]) -> None:
        """Persist a single turn's data to the store."""
        # Session handling
        self.store.insert_session(data["session_id"])
        self.store.update_session_end(data["session_id"], turns_increment=1)

        # Query log
        self.store.insert_query_log(data)

        # Retrieval log (optional)
        if "retrieval" in data:
            self.store.insert_retrieval_log(
                {"query_id": data["query_id"], **data["retrieval"]}
            )

        # Latency log (optional)
        if "latencies" in data:
            self.store.insert_latency_log(
                {"query_id": data["query_id"], **data["latencies"]}
            )

        # Quality log (optional)
        if "quality" in data:
            self.store.insert_quality_log(
                {"query_id": data["query_id"], **data["quality"]}
            )

        # Prune old data periodically
        self.store.prune_old(self.cfg["retention_days"])

    # ------------------------------------------------------------------
    # Façade methods
    # ------------------------------------------------------------------

    def get_dashboard(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Generate a dashboard payload."""
        return self.dashboard_generator.generate(time_window_hours)

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent alerts."""
        return self.alert_engine.get_recent_alerts(limit)

    def generate_report(self, hours: int = 24, label: str = "daily") -> str:
        """Generate an analytics report and return the file path."""
        path = self.report_generator.generate_custom_report(hours=hours, label=label)
        return str(path)

    def get_all_stats(self) -> Dict[str, Any]:
        """Return a combined stats snapshot from all analytics modules."""
        return {
            "query": self.query_analytics.get_stats(),
            "retrieval": self.retrieval_analytics.get_stats(),
            "conversation": self.conversation_analytics.get_stats(),
            "knowledge": self.knowledge_analytics.get_stats(),
            "alert_count": self.alert_engine.get_active_alert_count(),
        }

