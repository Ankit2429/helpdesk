"""Alert engine for Campus Helpdesk AI.

Monitors analytics events and system metrics against configurable thresholds.
When a threshold is breached the engine:

1. Persists the alert to the ``alerts`` table in :class:`MetricsStore`.
2. Publishes an ``AlertRaised`` event on the analytics :class:`EventBus`.
3. Enforces a configurable cooldown to prevent alert storms.

Alert Types
-----------
* ``HighLatency`` — end-to-end latency exceeds threshold.
* ``LowRetrievalQuality`` — retrieval score below minimum.
* ``HighHallucinationRate`` — hallucination flag rate above limit.
* ``SystemResourceWarning`` — CPU or RAM exceeds safe limits.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from campus_helpdesk.analytics.event_bus import EventBus
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


# Default thresholds — can be overridden via config
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "retrieval_latency_sec": 2.0,
    "llm_latency_sec": 5.0,
    "end_to_end_latency_sec": 8.0,
    "memory_mb": 500.0,
    "cpu_percent": 90.0,
    "hallucination_rate": 0.1,
    "min_retrieval_score": 0.3,
}

# Cooldown per alert type to prevent storm (seconds)
DEFAULT_COOLDOWN_SEC = 60.0


class Alert:
    """Immutable value object representing a single alert."""

    __slots__ = (
        "alert_id",
        "timestamp",
        "alert_type",
        "severity",
        "message",
        "metadata",
    )

    def __init__(
        self,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.alert_id: str = str(uuid.uuid4())
        self.timestamp: str = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.alert_type: str = alert_type
        self.severity: str = severity
        self.message: str = message
        self.metadata: Dict[str, Any] = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "metadata": self.metadata,
        }


class AlertEngine:
    """Threshold-based alert engine with cooldown and persistence.

    Parameters
    ----------
    store : MetricsStore
        Persistence backend (must have ``alerts`` table).
    event_bus : EventBus, optional
        If provided, subscribes to analytics events and publishes alerts.
    thresholds : dict, optional
        Override default thresholds.
    cooldown_seconds : float
        Minimum interval between repeated alerts of the same type.
    """

    EVENT_ALERT_RAISED = "AlertRaised"

    def __init__(
        self,
        store: "MetricsStore",
        event_bus: Optional["EventBus"] = None,
        thresholds: Optional[Dict[str, float]] = None,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SEC,
    ) -> None:
        self._store = store
        self._bus = event_bus
        self._thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._cooldown = cooldown_seconds
        self._lock = threading.Lock()

        # Last alert timestamp per alert_type for cooldown enforcement
        self._last_alert_time: Dict[str, float] = {}

        # In-memory recent alerts (bounded)
        self._recent_alerts: List[Alert] = []
        self._max_recent = 100

        if event_bus is not None:
            self._subscribe(event_bus)

    def _subscribe(self, bus: "EventBus") -> None:
        bus.subscribe("QueryCompleted", self._check_latency)
        bus.subscribe("RetrievalCompleted", self._check_retrieval_quality)
        bus.subscribe("SystemMetricRecorded", self._check_system_resources)
        logger.debug("AlertEngine subscribed to EventBus.")

    # ------------------------------------------------------------------
    # Threshold checks
    # ------------------------------------------------------------------

    def _check_latency(self, payload: Dict[str, Any]) -> None:
        """Check latency thresholds on QueryCompleted events."""
        try:
            meta = payload.get("metadata", {})
            latency_ms = payload.get("latency_ms") or meta.get("latency_ms")
            if latency_ms is None:
                return

            latency_sec = float(latency_ms) / 1000.0
            threshold = self._thresholds.get("end_to_end_latency_sec", 8.0)

            if latency_sec > threshold:
                self.raise_alert(
                    alert_type="HighLatency",
                    severity="WARNING",
                    message=(
                        f"End-to-end latency {latency_sec:.1f}s "
                        f"exceeds threshold {threshold:.1f}s"
                    ),
                    metadata={"latency_sec": latency_sec, "threshold_sec": threshold},
                )
        except Exception:
            logger.exception("AlertEngine: latency check failed.")

    def _check_retrieval_quality(self, payload: Dict[str, Any]) -> None:
        """Check retrieval score on RetrievalCompleted events."""
        try:
            meta = payload.get("metadata", {})
            score = meta.get("retrieval_score")
            if score is None:
                return

            threshold = self._thresholds.get("min_retrieval_score", 0.3)
            if float(score) < threshold:
                self.raise_alert(
                    alert_type="LowRetrievalQuality",
                    severity="WARNING",
                    message=(
                        f"Retrieval score {score:.3f} below "
                        f"threshold {threshold:.3f}"
                    ),
                    metadata={"score": score, "threshold": threshold},
                )
        except Exception:
            logger.exception("AlertEngine: retrieval quality check failed.")

    def _check_system_resources(self, payload: Dict[str, Any]) -> None:
        """Check CPU/RAM on SystemMetricRecorded events."""
        try:
            meta = payload.get("metadata", {})
            cpu = meta.get("cpu_percent", 0.0)
            ram = meta.get("ram_used_mb", 0.0)

            cpu_threshold = self._thresholds.get("cpu_percent", 90.0)
            ram_threshold = self._thresholds.get("memory_mb", 500.0)

            if float(cpu) > cpu_threshold:
                self.raise_alert(
                    alert_type="SystemResourceWarning",
                    severity="WARNING",
                    message=f"CPU usage {cpu:.1f}% exceeds threshold {cpu_threshold:.1f}%",
                    metadata={"cpu_percent": cpu, "threshold": cpu_threshold},
                )

            if float(ram) > ram_threshold:
                self.raise_alert(
                    alert_type="SystemResourceWarning",
                    severity="WARNING",
                    message=f"RAM usage {ram:.1f}MB exceeds threshold {ram_threshold:.1f}MB",
                    metadata={"ram_used_mb": ram, "threshold": ram_threshold},
                )
        except Exception:
            logger.exception("AlertEngine: system resource check failed.")

    # ------------------------------------------------------------------
    # Alert raising
    # ------------------------------------------------------------------

    def raise_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """Create, persist, and publish an alert if cooldown has elapsed.

        Returns the :class:`Alert` if raised, ``None`` if suppressed by
        cooldown.
        """
        with self._lock:
            now = time.monotonic()
            last = self._last_alert_time.get(alert_type, 0.0)
            if now - last < self._cooldown:
                logger.debug(
                    "Alert suppressed (cooldown): %s", alert_type
                )
                return None

            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                metadata=metadata,
            )
            self._last_alert_time[alert_type] = now

            # Persist
            self._persist_alert(alert)

            # Bounded in-memory buffer
            self._recent_alerts.append(alert)
            if len(self._recent_alerts) > self._max_recent:
                self._recent_alerts.pop(0)

        # Publish on EventBus (outside lock)
        if self._bus is not None:
            try:
                self._bus.publish(self.EVENT_ALERT_RAISED, alert.to_dict())
            except Exception:
                logger.exception("Failed to publish alert event.")

        logger.warning("ALERT [%s] %s: %s", severity, alert_type, message)
        return alert

    def _persist_alert(self, alert: Alert) -> None:
        """Write alert to the ``alerts`` table."""
        try:
            self._store.execute(
                "INSERT INTO alerts "
                "(alert_id, timestamp, alert_type, severity, message, resolved, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    alert.alert_id,
                    alert.timestamp,
                    alert.alert_type,
                    alert.severity,
                    alert.message,
                    0,
                    json.dumps(alert.metadata),
                ),
            )
        except Exception:
            logger.exception("Failed to persist alert %s.", alert.alert_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent alerts from memory."""
        with self._lock:
            return [a.to_dict() for a in self._recent_alerts[-limit:]]

    def get_active_alert_count(self) -> int:
        """Return the number of unresolved alerts in the database."""
        try:
            with self._store._lock:
                cur = self._store._conn.cursor()
                cur.execute("SELECT COUNT(*) FROM alerts WHERE resolved = 0")
                row = cur.fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    def reset_cooldowns(self) -> None:
        """Clear all cooldown timers (useful for testing)."""
        with self._lock:
            self._last_alert_time.clear()
