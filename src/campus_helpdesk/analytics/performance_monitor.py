"""System performance monitor for Campus Helpdesk AI.

Periodically samples CPU and RAM utilisation and persists the readings to
:class:`MetricsStore`.  Designed for Raspberry Pi — uses zero external
dependencies (no ``psutil``) by reading ``/proc`` on Linux and falling back
to :mod:`os` / :func:`resource.getrusage` on other platforms.

Usage::

    store = MetricsStore("data/analytics/metrics.sqlite")
    monitor = PerformanceMonitor(store, interval_seconds=10)
    monitor.start()
    # ... later ...
    monitor.stop()
"""

from __future__ import annotations

import logging
import os
import platform
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform-specific metric readers
# ---------------------------------------------------------------------------

_IS_LINUX = platform.system() == "Linux"


def _read_cpu_percent_linux() -> float:
    """Read instantaneous CPU usage from ``/proc/stat`` (Linux / RPi).

    Takes two snapshots 100 ms apart and computes the delta.  Returns a
    percentage in ``[0.0, 100.0]``.
    """
    try:

        def _snapshot() -> tuple[int, int]:
            with open("/proc/stat", encoding="utf-8") as fh:
                parts = fh.readline().split()
            # cpu user nice system idle iowait irq softirq steal guest guest_nice
            values = list(map(int, parts[1:]))
            idle = values[3] + values[4]  # idle + iowait
            total = sum(values)
            return idle, total

        idle1, total1 = _snapshot()
        time.sleep(0.1)
        idle2, total2 = _snapshot()

        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta <= 0:
            return 0.0
        return round((1.0 - idle_delta / total_delta) * 100.0, 2)
    except Exception:
        return 0.0


def _read_ram_used_mb_linux() -> float:
    """Read used RAM in MB from ``/proc/meminfo`` (Linux / RPi)."""
    try:
        mem: dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    mem[key] = int(parts[1])  # value in kB
        total_kb = mem.get("MemTotal", 0)
        available_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
        used_kb = total_kb - available_kb
        return round(used_kb / 1024.0, 2)
    except Exception:
        return 0.0


def _read_cpu_percent_fallback() -> float:
    """Cross-platform CPU usage estimate using :func:`os.getloadavg` or 0."""
    try:
        # os.getloadavg() is available on Unix-like systems.
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        return round(min(load1 / cpu_count * 100.0, 100.0), 2)
    except (AttributeError, OSError):
        # Windows: getloadavg not available — return 0 to avoid dependency.
        return 0.0


def _read_ram_used_mb_fallback() -> float:
    """Cross-platform RAM estimate — best-effort without ``psutil``."""
    try:
        import resource  # Unix only

        usage = resource.getrusage(resource.RUSAGE_SELF)
        # maxrss is in KB on Linux, bytes on macOS
        if platform.system() == "Darwin":
            return round(usage.ru_maxrss / (1024 * 1024), 2)
        return round(usage.ru_maxrss / 1024.0, 2)
    except (ImportError, AttributeError):
        return 0.0


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def read_system_metrics() -> tuple[float, float]:
    """Return ``(cpu_percent, ram_used_mb)`` using the best available method.

    On Linux / Raspberry Pi this reads ``/proc`` directly.  On other
    platforms it falls back to :func:`os.getloadavg` and :mod:`resource`.
    """
    if _IS_LINUX:
        return _read_cpu_percent_linux(), _read_ram_used_mb_linux()
    return _read_cpu_percent_fallback(), _read_ram_used_mb_fallback()


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------


class PerformanceMonitor:
    """Background thread that periodically records CPU/RAM to MetricsStore.

    Parameters
    ----------
    store : MetricsStore
        The persistence backend.
    interval_seconds : float
        Delay between successive snapshots.  Defaults to ``10``.
    """

    def __init__(
        self,
        store: MetricsStore,
        interval_seconds: float = 10.0,
    ) -> None:
        self._store = store
        self._interval = max(1.0, float(interval_seconds))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the background monitoring thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            logger.debug("PerformanceMonitor already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="PerfMonitor",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "PerformanceMonitor started (interval=%ss).", self._interval
        )

    def stop(self) -> None:
        """Signal the monitoring thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2)
            self._thread = None
        logger.info("PerformanceMonitor stopped.")

    # -- internals -----------------------------------------------------------

    def _run(self) -> None:
        """Polling loop executed in the background thread."""
        while not self._stop_event.is_set():
            try:
                cpu, ram = read_system_metrics()
                self._store.insert_system_metric(cpu, ram)
                logger.debug("System snapshot: cpu=%.1f%% ram=%.1fMB", cpu, ram)
            except Exception:
                logger.exception("PerformanceMonitor snapshot failed.")
            self._stop_event.wait(self._interval)

    # -- one-shot convenience ------------------------------------------------

    def snapshot(self) -> tuple[float, float]:
        """Take and persist a single snapshot immediately.

        Returns ``(cpu_percent, ram_used_mb)``.
        """
        cpu, ram = read_system_metrics()
        try:
            self._store.insert_system_metric(cpu, ram)
        except Exception:
            logger.exception("Failed to persist manual snapshot.")
        return cpu, ram
