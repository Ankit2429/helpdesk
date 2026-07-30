"""Integration tests for the analytics subsystem (Phase 2).

Tests end-to-end flows:
  EventBus → Analytics Modules → MetricsStore → Dashboard/Alerts/Reports

These tests use real SQLite databases (tmpdir) and real EventBus instances
to verify the full integration path.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from campus_helpdesk.analytics.alert_engine import AlertEngine
from campus_helpdesk.analytics.analytics_manager import AnalyticsManager
from campus_helpdesk.analytics.conversation_analytics import ConversationAnalytics
from campus_helpdesk.analytics.dashboard_generator import DashboardGenerator
from campus_helpdesk.analytics.event_bus import EventBus
from campus_helpdesk.analytics.knowledge_analytics import KnowledgeAnalytics
from campus_helpdesk.analytics.metrics_store import MetricsStore
from campus_helpdesk.analytics.pipeline_trace import PipelineTrace
from campus_helpdesk.analytics.query_analytics import QueryAnalytics
from campus_helpdesk.analytics.report_generator import ReportGenerator
from campus_helpdesk.analytics.retrieval_analytics import RetrievalAnalytics


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def analytics_stack(tmp_path):
    """Create a complete analytics stack with real components."""
    db_path = str(tmp_path / "integration.sqlite")
    store = MetricsStore(db_path)
    bus = EventBus()

    # Wire all modules
    qa = QueryAnalytics(store, bus)
    ra = RetrievalAnalytics(store, bus)
    ca = ConversationAnalytics(store, bus)
    ka = KnowledgeAnalytics(store, bus)
    ae = AlertEngine(store, bus, cooldown_seconds=0)
    dg = DashboardGenerator(store)
    rg = ReportGenerator(store, output_dir=tmp_path / "reports", dashboard_generator=dg)

    yield {
        "store": store,
        "bus": bus,
        "query_analytics": qa,
        "retrieval_analytics": ra,
        "conversation_analytics": ca,
        "knowledge_analytics": ka,
        "alert_engine": ae,
        "dashboard_generator": dg,
        "report_generator": rg,
        "tmp_path": tmp_path,
    }
    store.close()


# =====================================================================
# Integration Tests
# =====================================================================


class TestFullEventFlow:
    """Test events flowing from EventBus through analytics to MetricsStore."""

    def test_query_event_flow(self, analytics_stack):
        """QueryReceived → QueryAnalytics → MetricsStore → Dashboard."""
        bus = analytics_stack["bus"]
        store = analytics_stack["store"]
        qa = analytics_stack["query_analytics"]
        dg = analytics_stack["dashboard_generator"]

        # Simulate a session
        store.insert_session("s1")

        # Publish query events
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryReceived",
            metadata={"intent": "admission_info", "raw_query": "How to apply?"},
        )
        bus.publish("QueryReceived", payload)
        time.sleep(0.3)

        # Complete the query
        complete_payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryCompleted",
            metadata={
                "status": "success",
                "raw_query": "How to apply?",
                "intent": "admission_info",
            },
        )
        bus.publish("QueryCompleted", complete_payload)
        time.sleep(0.3)

        # Verify in-memory stats
        stats = qa.get_stats()
        assert stats["total_queries"] == 1
        assert stats["intent_distribution"]["admission_info"] == 1

        # Verify MetricsStore
        row = store.fetchone("SELECT * FROM query_logs WHERE query_id = 'q1'")
        assert row is not None
        assert row["status"] == "success"

        # Verify Dashboard
        dashboard = dg.generate(time_window_hours=1)
        assert dashboard["summary"]["total_queries"] >= 1

    def test_retrieval_event_flow(self, analytics_stack):
        """RetrievalCompleted → RetrievalAnalytics + KnowledgeAnalytics → MetricsStore."""
        bus = analytics_stack["bus"]
        store = analytics_stack["store"]
        ra = analytics_stack["retrieval_analytics"]
        ka = analytics_stack["knowledge_analytics"]

        store.insert_session("s1")
        store.insert_query_log({"query_id": "q1", "session_id": "s1"})

        payload = PipelineTrace.event_payload(
            trace_id="q1",
            component="Retriever",
            event_type="RetrievalCompleted",
            metadata={
                "retrieved_chunk_ids": ["chunk_1", "chunk_2", "chunk_3"],
                "source_documents": ["admissions.md", "fees.md"],
                "retrieval_score": 0.85,
                "cross_encoder_score": 0.92,
                "unused_docs_count": 1,
                "raw_query": "How to apply?",
            },
        )
        bus.publish("RetrievalCompleted", payload)
        time.sleep(0.3)

        # RetrievalAnalytics
        r_stats = ra.get_stats()
        assert r_stats["total_retrievals"] == 1
        assert abs(r_stats["avg_retrieval_score"] - 0.85) < 0.01

        # KnowledgeAnalytics
        k_stats = ka.get_stats()
        assert k_stats["total_events"] == 1
        assert k_stats["unique_documents_accessed"] == 2

        # MetricsStore
        row = store.fetchone("SELECT * FROM retrieval_logs WHERE query_id = 'q1'")
        assert row is not None

    def test_conversation_lifecycle_flow(self, analytics_stack):
        """SessionStarted → TurnCompleted → SessionEnded → ConversationAnalytics."""
        bus = analytics_stack["bus"]
        ca = analytics_stack["conversation_analytics"]

        bus.publish("SessionStarted", {"session_id": "s1"})
        time.sleep(0.2)
        bus.publish("TurnCompleted", {"session_id": "s1", "metadata": {"topic": "admission"}})
        time.sleep(0.2)
        bus.publish("TurnCompleted", {"session_id": "s1", "metadata": {"topic": "fees"}})
        time.sleep(0.2)
        bus.publish("SessionEnded", {"session_id": "s1"})
        time.sleep(0.3)

        stats = ca.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["total_turns"] == 2
        assert stats["active_sessions"] == 0
        assert "admission" in stats["topic_distribution"]
        assert "fees" in stats["topic_distribution"]

    def test_alert_triggered_by_event(self, analytics_stack):
        """QueryCompleted with high latency → AlertEngine → alert persisted."""
        bus = analytics_stack["bus"]
        ae = analytics_stack["alert_engine"]
        store = analytics_stack["store"]

        payload = {
            "latency_ms": 15000,  # 15 seconds — exceeds default threshold
            "metadata": {},
        }
        bus.publish("QueryCompleted", payload)
        time.sleep(0.3)

        alerts = ae.get_recent_alerts()
        assert len(alerts) >= 1
        assert any(a["alert_type"] == "HighLatency" for a in alerts)

        # Verify persisted
        db_alerts = store.get_alerts()
        assert len(db_alerts) >= 1


class TestAnalyticsManagerIntegration:
    """Test the AnalyticsManager wiring everything together."""

    def test_full_lifecycle(self, tmp_path):
        cfg = {
            "database_path": str(tmp_path / "mgr.sqlite"),
            "system_monitor_interval_seconds": 60,
            "report_output_dir": str(tmp_path / "reports"),
        }
        mgr = AnalyticsManager(config=cfg)
        mgr.start()

        # Track a turn via the queue
        mgr.track_turn({
            "query_id": "q1",
            "session_id": "s1",
            "raw_query": "What are the fees?",
            "status": "success",
            "intent": "fees",
            "latencies": {"end_to_end": 250.0, "retrieval": 50.0},
            "quality": {"confidence_score": 0.9, "citation_coverage": 0.8},
            "retrieval": {
                "retrieved_chunk_ids": ["c1", "c2"],
                "retrieval_score": 0.88,
            },
        })
        time.sleep(1.0)

        # Verify data was persisted
        row = mgr.store.fetchone("SELECT * FROM query_logs WHERE query_id = 'q1'")
        assert row is not None

        lat_row = mgr.store.fetchone("SELECT * FROM latency_logs WHERE query_id = 'q1'")
        assert lat_row is not None
        assert abs(lat_row["end_to_end"] - 250.0) < 0.01

        # Verify dashboard works
        dashboard = mgr.get_dashboard()
        assert dashboard["summary"]["total_queries"] >= 1

        # Verify report generation
        report_path = mgr.generate_report(hours=1, label="integration_test")
        assert Path(report_path).exists()

        # Verify stats
        stats = mgr.get_all_stats()
        assert "query" in stats
        assert "retrieval" in stats

        mgr.stop()

    def test_event_publishing(self, tmp_path):
        cfg = {
            "database_path": str(tmp_path / "mgr2.sqlite"),
            "system_monitor_interval_seconds": 60,
        }
        mgr = AnalyticsManager(config=cfg)
        mgr.start()

        # Publish events through the manager
        mgr.store.insert_session("s1")
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryReceived",
            metadata={"intent": "library"},
        )
        mgr.publish_event("QueryReceived", payload)
        time.sleep(0.5)

        # QueryAnalytics should have picked it up
        stats = mgr.query_analytics.get_stats()
        assert stats["total_queries"] >= 1

        mgr.stop()

    def test_multiple_turns_queued(self, tmp_path):
        cfg = {
            "database_path": str(tmp_path / "mgr3.sqlite"),
            "system_monitor_interval_seconds": 60,
        }
        mgr = AnalyticsManager(config=cfg)
        mgr.start()

        for i in range(10):
            mgr.track_turn({
                "query_id": f"q{i}",
                "session_id": "s1",
                "raw_query": f"Question {i}",
                "status": "success",
            })

        time.sleep(2.0)
        mgr.stop()

        stats = mgr.store.get_query_stats()
        assert stats["total_queries"] == 10


class TestDashboardWithRealData:
    """Verify dashboard generation with realistic data."""

    def test_latency_percentiles(self, analytics_stack):
        store = analytics_stack["store"]
        dg = analytics_stack["dashboard_generator"]

        # Insert multiple queries with varying latencies
        store.insert_session("s1")
        for i in range(20):
            qid = f"q{i}"
            store.insert_query_log({"query_id": qid, "session_id": "s1", "status": "success"})
            store.insert_latency_log({"query_id": qid, "end_to_end": float(100 + i * 50)})

        dashboard = dg.generate(time_window_hours=1)
        latency = dashboard["latency"]
        assert latency["sample_count"] == 20
        assert latency["p50_ms"] > 0
        assert latency["p90_ms"] > latency["p50_ms"]

    def test_quality_aggregation(self, analytics_stack):
        store = analytics_stack["store"]
        dg = analytics_stack["dashboard_generator"]

        store.insert_session("s1")
        for i in range(5):
            qid = f"q{i}"
            store.insert_query_log({"query_id": qid, "session_id": "s1", "status": "success"})
            store.insert_quality_log({
                "query_id": qid,
                "confidence_score": 0.8 + i * 0.02,
                "citation_coverage": 0.7,
                "hallucination_flag": i == 4,
            })

        dashboard = dg.generate(time_window_hours=1)
        quality = dashboard["quality"]
        assert quality["sample_count"] == 5
        assert quality["avg_confidence"] > 0
        assert quality["hallucination_rate"] == pytest.approx(0.2, abs=0.01)


class TestReportWithRealData:
    """Verify report generation with real data."""

    def test_report_includes_all_sections(self, analytics_stack):
        store = analytics_stack["store"]
        rg = analytics_stack["report_generator"]

        store.insert_session("s1")
        store.insert_query_log({
            "query_id": "q1", "session_id": "s1",
            "status": "success", "intent": "fees",
        })
        store.insert_latency_log({"query_id": "q1", "end_to_end": 200.0})

        path = rg.generate_daily_report()
        content = path.read_text(encoding="utf-8")

        assert "Summary" in content
        assert "Latency" in content
        assert "Quality" in content
        assert "System Health" in content
