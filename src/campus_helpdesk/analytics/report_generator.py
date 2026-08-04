"""Report generator for Campus Helpdesk AI analytics.

Produces Markdown and JSON summary reports from :class:`MetricsStore` data.
Reports can be generated on demand or scheduled for daily/weekly summaries.

Output files are written to a configurable directory.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from campus_helpdesk.analytics.dashboard_generator import DashboardGenerator
    from campus_helpdesk.analytics.metrics_store import MetricsStore

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates Markdown and JSON analytics reports.

    Parameters
    ----------
    store : MetricsStore
        The SQLite persistence backend.
    output_dir : str or Path
        Directory for report output files.
    dashboard_generator : DashboardGenerator, optional
        If provided, used to produce dashboard data sections.
    """

    def __init__(
        self,
        store: MetricsStore,
        output_dir: str | Path = "data/analytics/reports",
        dashboard_generator: DashboardGenerator | None = None,
    ) -> None:
        self._store = store
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._dashboard = dashboard_generator

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_daily_report(self) -> Path:
        """Generate a daily summary report (Markdown + JSON).

        Returns the path to the generated Markdown report file.
        """
        return self._generate_report(hours=24, label="daily")

    def generate_weekly_report(self) -> Path:
        """Generate a weekly summary report (Markdown + JSON).

        Returns the path to the generated Markdown report file.
        """
        return self._generate_report(hours=168, label="weekly")

    def generate_custom_report(self, hours: int = 24, label: str = "custom") -> Path:
        """Generate a report for an arbitrary time window."""
        return self._generate_report(hours=hours, label=label)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _generate_report(self, hours: int, label: str) -> Path:
        """Core report generation logic."""
        now = datetime.now(UTC)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")

        # Collect data
        data = self._collect_data(hours)

        # Generate Markdown
        md_content = self._render_markdown(data, hours, label, now)
        md_path = self._output_dir / f"report_{label}_{timestamp_str}.md"
        md_path.write_text(md_content, encoding="utf-8")

        # Generate JSON
        json_path = self._output_dir / f"report_{label}_{timestamp_str}.json"
        json_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

        logger.info("Generated %s report: %s", label, md_path)
        return md_path

    def _collect_data(self, hours: int) -> dict[str, Any]:
        """Collect all report data from the store."""
        if self._dashboard is not None:
            dashboard_data = self._dashboard.generate(time_window_hours=hours)
        else:
            dashboard_data = {}

        # Additional direct queries
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

        alerts = self._get_alerts(cutoff_str)
        intent_dist = self._get_intent_distribution(cutoff_str)

        return {
            "dashboard": dashboard_data,
            "alerts": alerts,
            "intent_distribution": intent_dist,
            "report_period_hours": hours,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _get_alerts(self, cutoff: str) -> list[dict[str, Any]]:
        """Fetch alerts within the time window."""
        try:
            with self._store._lock:
                cur = self._store._conn.cursor()
                cur.execute(
                    "SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC",
                    (cutoff,),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            logger.debug("No alerts table or query failed.")
            return []

    def _get_intent_distribution(self, cutoff: str) -> dict[str, int]:
        """Get intent distribution within the time window."""
        try:
            with self._store._lock:
                cur = self._store._conn.cursor()
                cur.execute(
                    "SELECT intent, COUNT(*) as cnt FROM query_logs "
                    "WHERE timestamp >= ? AND intent IS NOT NULL "
                    "GROUP BY intent ORDER BY cnt DESC",
                    (cutoff,),
                )
                return {row["intent"]: row["cnt"] for row in cur.fetchall()}
        except Exception:
            return {}

    def _render_markdown(
        self,
        data: dict[str, Any],
        hours: int,
        label: str,
        generated_at: datetime,
    ) -> str:
        """Render report data as Markdown."""
        dashboard = data.get("dashboard", {})
        summary = dashboard.get("summary", {})
        latency = dashboard.get("latency", {})
        quality = dashboard.get("quality", {})
        health = dashboard.get("system_health", {})
        alerts = data.get("alerts", [])
        intent_dist = data.get("intent_distribution", {})

        lines: list[str] = []
        lines.append(f"# Analytics Report — {label.capitalize()}")
        lines.append("")
        lines.append(
            f"**Generated:** {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        lines.append(f"**Period:** Last {hours} hours")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Queries | {summary.get('total_queries', 0)} |")
        lines.append(f"| Total Sessions | {summary.get('total_sessions', 0)} |")
        lines.append(
            f"| Success Rate | {summary.get('success_rate', 0):.1%} |"
        )
        lines.append("")

        # Status Distribution
        status_dist = summary.get("status_distribution", {})
        if status_dist:
            lines.append("### Status Distribution")
            lines.append("")
            for status, count in status_dist.items():
                lines.append(f"- **{status}**: {count}")
            lines.append("")

        # Latency
        lines.append("## Latency")
        lines.append("")
        lines.append("| Percentile | Value (ms) |")
        lines.append("|-----------|-----------|")
        lines.append(f"| P50 | {latency.get('p50_ms', 0):.1f} |")
        lines.append(f"| P90 | {latency.get('p90_ms', 0):.1f} |")
        lines.append(f"| P99 | {latency.get('p99_ms', 0):.1f} |")
        lines.append(f"| Average | {latency.get('avg_ms', 0):.1f} |")
        lines.append(
            f"| Samples | {latency.get('sample_count', 0)} |"
        )
        lines.append("")

        # Quality
        lines.append("## Quality")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(
            f"| Avg Confidence | {quality.get('avg_confidence', 0):.3f} |"
        )
        lines.append(
            f"| Avg Citation Coverage | {quality.get('avg_citation_coverage', 0):.3f} |"
        )
        lines.append(
            f"| Hallucination Rate | {quality.get('hallucination_rate', 0):.3f} |"
        )
        lines.append("")

        # System Health
        lines.append("## System Health")
        lines.append("")
        lines.append(f"- **CPU:** {health.get('cpu_percent', 0):.1f}%")
        lines.append(f"- **RAM:** {health.get('ram_used_mb', 0):.1f} MB")
        lines.append(
            f"- **Last Updated:** {health.get('last_updated', 'N/A')}"
        )
        lines.append("")

        # Alerts
        if alerts:
            lines.append("## Alerts")
            lines.append("")
            lines.append("| Time | Type | Severity | Message |")
            lines.append("|------|------|----------|---------|")
            for alert in alerts[:20]:
                ts = alert.get("timestamp", "")
                atype = alert.get("alert_type", "")
                sev = alert.get("severity", "")
                msg = alert.get("message", "")
                lines.append(f"| {ts} | {atype} | {sev} | {msg} |")
            lines.append("")

        # Intent Distribution
        if intent_dist:
            lines.append("## Intent Distribution")
            lines.append("")
            for intent, count in list(intent_dist.items())[:15]:
                lines.append(f"- **{intent}**: {count}")
            lines.append("")

        lines.append("---")
        lines.append("*Report generated by Campus Helpdesk Analytics*")

        return "\n".join(lines)
