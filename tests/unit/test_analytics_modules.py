"""Unit tests for the analytics package (Phase 2).

Tests all 8 analytics modules with mocked MetricsStore and EventBus.
Target coverage: ≥90% for campus_helpdesk.analytics.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import time
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from campus_helpdesk.analytics.alert_engine import Alert, AlertEngine
from campus_helpdesk.analytics.analytics_manager import AnalyticsManager
from campus_helpdesk.analytics.conversation_analytics import ConversationAnalytics
from campus_helpdesk.analytics.dashboard_generator import DashboardGenerator
from campus_helpdesk.analytics.event_bus import EventBus
from campus_helpdesk.analytics.knowledge_analytics import KnowledgeAnalytics
from campus_helpdesk.analytics.metrics_store import MetricsStore
from campus_helpdesk.analytics.performance_monitor import (
    PerformanceMonitor,
    read_system_metrics,
)
from campus_helpdesk.analytics.pipeline_trace import PipelineTrace
from campus_helpdesk.analytics.query_analytics import QueryAnalytics
from campus_helpdesk.analytics.report_generator import ReportGenerator
from campus_helpdesk.analytics.retrieval_analytics import RetrievalAnalytics


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary MetricsStore backed by a temp SQLite file."""
    db_path = str(tmp_path / "test_metrics.sqlite")
    store = MetricsStore(db_path)
    yield store
    store.close()


@pytest.fixture
def event_bus():
    """Fresh EventBus instance."""
    return EventBus()


# =====================================================================
# EventBus Tests
# =====================================================================


class TestEventBus:
    def test_subscribe_and_publish(self, event_bus):
        received = []
        event_bus.subscribe("TestEvent", lambda p: received.append(p))
        event_bus.publish("TestEvent", {"key": "value"})
        time.sleep(0.1)  # handler runs in daemon thread
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_unsubscribe(self, event_bus):
        received = []
        handler = lambda p: received.append(p)
        event_bus.subscribe("E", handler)
        event_bus.unsubscribe("E", handler)
        event_bus.publish("E", {})
        time.sleep(0.1)
        assert len(received) == 0

    def test_multiple_handlers(self, event_bus):
        results = {"a": 0, "b": 0}
        event_bus.subscribe("E", lambda p: results.__setitem__("a", 1))
        event_bus.subscribe("E", lambda p: results.__setitem__("b", 1))
        event_bus.publish("E", {})
        time.sleep(0.2)
        assert results["a"] == 1
        assert results["b"] == 1

    def test_publish_no_subscribers(self, event_bus):
        # Should not raise
        event_bus.publish("NoSubs", {"data": 1})


# =====================================================================
# PipelineTrace Tests
# =====================================================================


class TestPipelineTrace:
    def test_new_trace_id(self):
        tid = PipelineTrace.new_trace_id()
        assert isinstance(tid, str)
        assert len(tid) == 36  # UUID4 format

    def test_event_payload(self):
        payload = PipelineTrace.event_payload(
            trace_id="abc-123",
            session_id="session-1",
            component="Retriever",
            event_type="RetrievalCompleted",
            latency_ms=42.5,
            metadata={"chunks": 3},
        )
        assert payload["trace_id"] == "abc-123"
        assert payload["session_id"] == "session-1"
        assert payload["component"] == "Retriever"
        assert payload["event_type"] == "RetrievalCompleted"
        assert payload["latency_ms"] == 42.5
        assert payload["metadata"]["chunks"] == 3
        assert payload["severity"] == "INFO"
        assert "timestamp" in payload


# =====================================================================
# MetricsStore Tests
# =====================================================================


class TestMetricsStore:
    def test_schema_creation(self, tmp_db):
        """All tables should exist after init."""
        tables = tmp_db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = {row["name"] for row in tables}
        expected = {
            "sessions", "query_logs", "retrieval_logs",
            "latency_logs", "quality_logs", "system_metrics",
            "alerts", "pipeline_traces",
        }
        assert expected.issubset(table_names)

    def test_insert_and_query_session(self, tmp_db):
        tmp_db.insert_session("s1")
        row = tmp_db.fetchone("SELECT * FROM sessions WHERE session_id = 's1'")
        assert row is not None
        assert row["session_id"] == "s1"

    def test_insert_query_log(self, tmp_db):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({
            "query_id": "q1",
            "session_id": "s1",
            "raw_query": "What is the library timing?",
            "intent": "library_info",
            "status": "success",
        })
        row = tmp_db.fetchone("SELECT * FROM query_logs WHERE query_id = 'q1'")
        assert row is not None
        assert row["raw_query"] == "What is the library timing?"

    def test_insert_retrieval_log(self, tmp_db):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1"})
        tmp_db.insert_retrieval_log({
            "query_id": "q1",
            "retrieved_chunk_ids": ["c1", "c2"],
            "retrieval_score": 0.85,
        })
        row = tmp_db.fetchone("SELECT * FROM retrieval_logs WHERE query_id = 'q1'")
        assert row is not None
        assert abs(row["retrieval_score"] - 0.85) < 0.001

    def test_insert_latency_log(self, tmp_db):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1"})
        tmp_db.insert_latency_log({
            "query_id": "q1",
            "retrieval": 15.0,
            "llm_generation": 200.0,
            "end_to_end": 300.0,
        })
        row = tmp_db.fetchone("SELECT * FROM latency_logs WHERE query_id = 'q1'")
        assert row is not None
        assert abs(row["end_to_end"] - 300.0) < 0.001

    def test_insert_quality_log(self, tmp_db):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1"})
        tmp_db.insert_quality_log({
            "query_id": "q1",
            "confidence_score": 0.92,
            "hallucination_flag": False,
            "citation_coverage": 0.8,
        })
        row = tmp_db.fetchone("SELECT * FROM quality_logs WHERE query_id = 'q1'")
        assert row is not None
        assert abs(row["confidence_score"] - 0.92) < 0.001

    def test_insert_system_metric(self, tmp_db):
        tmp_db.insert_system_metric(45.2, 512.0)
        row = tmp_db.fetchone("SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT 1")
        assert row is not None
        assert abs(row["cpu_percent"] - 45.2) < 0.1

    def test_insert_pipeline_trace(self, tmp_db):
        tmp_db.insert_pipeline_trace({
            "trace_id": "t1",
            "session_id": "s1",
            "component": "Retriever",
            "event_type": "RetrievalCompleted",
            "latency_ms": 42.5,
            "metadata": {"chunks": 3},
        })
        row = tmp_db.fetchone("SELECT * FROM pipeline_traces WHERE trace_id = 't1'")
        assert row is not None
        assert row["component"] == "Retriever"

    def test_get_query_stats(self, tmp_db):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1", "status": "success"})
        tmp_db.insert_query_log({"query_id": "q2", "session_id": "s1", "status": "failed"})
        stats = tmp_db.get_query_stats()
        assert stats["total_queries"] == 2
        assert stats["status_distribution"]["success"] == 1
        assert stats["status_distribution"]["failed"] == 1

    def test_get_alerts(self, tmp_db):
        tmp_db.execute(
            "INSERT INTO alerts (alert_id, alert_type, severity, message) VALUES (?, ?, ?, ?)",
            ("a1", "HighLatency", "WARNING", "Latency is high"),
        )
        alerts = tmp_db.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "HighLatency"

    def test_prune_old(self, tmp_db):
        """Pruning should not raise, even on an empty database."""
        tmp_db.prune_old(30)

    def test_duplicate_query_id_ignored(self, tmp_db):
        """INSERT OR IGNORE should skip duplicate query_ids."""
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1", "status": "success"})
        # Second insert with same query_id should not raise
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1", "status": "failed"})
        rows = tmp_db.fetchall("SELECT * FROM query_logs WHERE query_id = 'q1'")
        assert len(rows) == 1  # only the first insert survived


# =====================================================================
# PerformanceMonitor Tests
# =====================================================================


class TestPerformanceMonitor:
    def test_read_system_metrics(self):
        cpu, ram = read_system_metrics()
        assert isinstance(cpu, float)
        assert isinstance(ram, float)
        assert cpu >= 0.0
        assert ram >= 0.0

    def test_start_stop(self, tmp_db):
        monitor = PerformanceMonitor(tmp_db, interval_seconds=1)
        monitor.start()
        time.sleep(0.5)
        monitor.stop()
        # Should not raise on double-stop
        monitor.stop()

    def test_snapshot(self, tmp_db):
        monitor = PerformanceMonitor(tmp_db, interval_seconds=60)
        cpu, ram = monitor.snapshot()
        assert isinstance(cpu, float)
        assert isinstance(ram, float)

    def test_idempotent_start(self, tmp_db):
        monitor = PerformanceMonitor(tmp_db, interval_seconds=60)
        monitor.start()
        monitor.start()  # should not raise
        monitor.stop()


# =====================================================================
# QueryAnalytics Tests
# =====================================================================


class TestQueryAnalytics:
    def test_handle_query_received(self, tmp_db, event_bus):
        qa = QueryAnalytics(tmp_db, event_bus)
        payload = PipelineTrace.event_payload(
            trace_id="t1",
            component="Pipeline",
            event_type="QueryReceived",
            metadata={"intent": "admission_info", "has_followup": True},
        )
        qa.handle_query_received(payload)
        stats = qa.get_stats()
        assert stats["total_queries"] == 1
        assert stats["intent_distribution"]["admission_info"] == 1
        assert stats["followup_rate"] == 1.0

    def test_handle_query_completed(self, tmp_db, event_bus):
        qa = QueryAnalytics(tmp_db, event_bus)
        tmp_db.insert_session("s1")
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryCompleted",
            metadata={"status": "success", "raw_query": "test"},
        )
        qa.handle_query_completed(payload)
        stats = qa.get_stats()
        assert stats["status_distribution"]["success"] == 1

    def test_handle_query_failed(self, tmp_db, event_bus):
        qa = QueryAnalytics(tmp_db, event_bus)
        tmp_db.insert_session("s1")
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryFailed",
            metadata={"raw_query": "broken query"},
        )
        qa.handle_query_failed(payload)
        stats = qa.get_stats()
        assert stats["status_distribution"]["failed"] == 1

    def test_reset(self, tmp_db):
        qa = QueryAnalytics(tmp_db)
        qa.handle_query_received({"metadata": {"intent": "test"}})
        qa.reset()
        assert qa.get_stats()["total_queries"] == 0

    def test_event_bus_integration(self, tmp_db, event_bus):
        """Events published on the bus should reach QueryAnalytics."""
        qa = QueryAnalytics(tmp_db, event_bus)
        tmp_db.insert_session("s1")
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            session_id="s1",
            component="Pipeline",
            event_type="QueryReceived",
            metadata={"intent": "fees"},
        )
        event_bus.publish("QueryReceived", payload)
        time.sleep(0.3)
        stats = qa.get_stats()
        assert stats["total_queries"] == 1


# =====================================================================
# RetrievalAnalytics Tests
# =====================================================================


class TestRetrievalAnalytics:
    def test_handle_retrieval_completed(self, tmp_db, event_bus):
        ra = RetrievalAnalytics(tmp_db, event_bus)
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({"query_id": "q1", "session_id": "s1"})
        payload = PipelineTrace.event_payload(
            trace_id="q1",
            component="Retriever",
            event_type="RetrievalCompleted",
            metadata={
                "retrieved_chunk_ids": ["c1", "c2", "c3"],
                "retrieval_score": 0.85,
                "cross_encoder_score": 0.92,
                "unused_docs_count": 2,
            },
        )
        ra.handle_retrieval_completed(payload)
        stats = ra.get_stats()
        assert stats["total_retrievals"] == 1
        assert abs(stats["avg_retrieval_score"] - 0.85) < 0.01
        assert abs(stats["avg_cross_encoder_score"] - 0.92) < 0.01

    def test_bounded_history(self, tmp_db):
        ra = RetrievalAnalytics(tmp_db, max_history=5)
        for i in range(10):
            ra.handle_retrieval_completed({
                "trace_id": f"q{i}",
                "metadata": {"retrieval_score": float(i), "retrieved_chunk_ids": []},
            })
        assert ra.get_stats()["score_buffer_size"] == 5

    def test_reset(self, tmp_db):
        ra = RetrievalAnalytics(tmp_db)
        ra.handle_retrieval_completed({
            "trace_id": "q1",
            "metadata": {"retrieval_score": 0.5, "retrieved_chunk_ids": ["c1"]},
        })
        ra.reset()
        assert ra.get_stats()["total_retrievals"] == 0


# =====================================================================
# ConversationAnalytics Tests
# =====================================================================


class TestConversationAnalytics:
    def test_session_lifecycle(self, tmp_db, event_bus):
        ca = ConversationAnalytics(tmp_db, event_bus)
        ca.handle_session_started({"session_id": "s1"})
        ca.handle_turn_completed({"session_id": "s1", "metadata": {"topic": "fees"}})
        ca.handle_turn_completed({"session_id": "s1", "metadata": {"topic": "fees"}})
        ca.handle_session_ended({"session_id": "s1"})

        stats = ca.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["total_turns"] == 2
        assert stats["active_sessions"] == 0
        assert stats["topic_distribution"]["fees"] == 2

    def test_avg_turns_per_session(self, tmp_db):
        ca = ConversationAnalytics(tmp_db)
        ca.handle_session_started({"session_id": "s1"})
        ca.handle_turn_completed({"session_id": "s1", "metadata": {}})
        ca.handle_turn_completed({"session_id": "s1", "metadata": {}})
        ca.handle_session_ended({"session_id": "s1"})

        stats = ca.get_stats()
        assert stats["avg_turns_per_session"] == 2.0

    def test_reset(self, tmp_db):
        ca = ConversationAnalytics(tmp_db)
        ca.handle_session_started({"session_id": "s1"})
        ca.reset()
        assert ca.get_stats()["total_sessions"] == 0


# =====================================================================
# KnowledgeAnalytics Tests
# =====================================================================


class TestKnowledgeAnalytics:
    def test_document_access_tracking(self, tmp_db):
        ka = KnowledgeAnalytics(tmp_db)
        ka.handle_retrieval_completed({
            "metadata": {
                "retrieved_chunk_ids": ["c1", "c2"],
                "source_documents": ["doc_a.md", "doc_b.md"],
                "retrieval_score": 0.9,
            }
        })
        most = ka.get_most_accessed_documents(top_n=5)
        assert len(most) == 2

    def test_unknown_question_detection(self, tmp_db):
        ka = KnowledgeAnalytics(tmp_db)
        ka.handle_retrieval_completed({
            "metadata": {
                "retrieved_chunk_ids": [],
                "source_documents": [],
                "retrieval_score": 0.1,
                "raw_query": "What is the meaning of life?",
            }
        })
        unknowns = ka.get_unknown_questions()
        assert len(unknowns) == 1
        assert "meaning of life" in unknowns[0]["question"]

    def test_query_failed_records_unknown(self, tmp_db):
        ka = KnowledgeAnalytics(tmp_db)
        ka.handle_query_failed({
            "metadata": {"raw_query": "Tell me about aliens"}
        })
        assert len(ka.get_unknown_questions()) == 1

    def test_bounded_unknown_questions(self, tmp_db):
        ka = KnowledgeAnalytics(tmp_db, max_unknown_questions=3)
        for i in range(5):
            ka.handle_query_failed({"metadata": {"raw_query": f"q{i}"}})
        assert len(ka.get_unknown_questions()) == 3

    def test_reset(self, tmp_db):
        ka = KnowledgeAnalytics(tmp_db)
        ka.handle_retrieval_completed({
            "metadata": {
                "retrieved_chunk_ids": ["c1"],
                "source_documents": ["doc.md"],
                "retrieval_score": 0.9,
            }
        })
        ka.reset()
        assert ka.get_stats()["total_events"] == 0


# =====================================================================
# DashboardGenerator Tests
# =====================================================================


class TestDashboardGenerator:
    def test_generate_empty_db(self, tmp_db):
        dg = DashboardGenerator(tmp_db)
        data = dg.generate(time_window_hours=24)
        assert "summary" in data
        assert "latency" in data
        assert "quality" in data
        assert "system_health" in data
        assert data["summary"]["total_queries"] == 0

    def test_generate_with_data(self, tmp_db):
        # Insert some data
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({
            "query_id": "q1", "session_id": "s1", "status": "success"
        })
        tmp_db.insert_latency_log({
            "query_id": "q1", "end_to_end": 150.0
        })
        tmp_db.insert_quality_log({
            "query_id": "q1", "confidence_score": 0.9, "citation_coverage": 0.8
        })
        tmp_db.insert_system_metric(30.0, 256.0)

        dg = DashboardGenerator(tmp_db)
        data = dg.generate(time_window_hours=24)
        assert data["summary"]["total_queries"] == 1
        assert data["system_health"]["cpu_percent"] == 30.0


# =====================================================================
# AlertEngine Tests
# =====================================================================


class TestAlertEngine:
    def test_raise_alert(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=0)
        alert = ae.raise_alert("TestAlert", "WARNING", "Test message")
        assert alert is not None
        assert alert.alert_type == "TestAlert"

    def test_cooldown_suppression(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=60)
        a1 = ae.raise_alert("TestAlert", "WARNING", "First")
        a2 = ae.raise_alert("TestAlert", "WARNING", "Second")
        assert a1 is not None
        assert a2 is None  # suppressed by cooldown

    def test_different_types_not_suppressed(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=60)
        a1 = ae.raise_alert("TypeA", "WARNING", "A")
        a2 = ae.raise_alert("TypeB", "WARNING", "B")
        assert a1 is not None
        assert a2 is not None

    def test_persist_alert(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=0)
        ae.raise_alert("HighLatency", "WARNING", "Latency exceeded")
        alerts = tmp_db.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "HighLatency"

    def test_recent_alerts(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=0)
        ae.raise_alert("A", "WARNING", "msg1")
        ae.raise_alert("B", "WARNING", "msg2")
        recent = ae.get_recent_alerts()
        assert len(recent) == 2

    def test_latency_check(self, tmp_db, event_bus):
        ae = AlertEngine(
            tmp_db, event_bus,
            thresholds={"end_to_end_latency_sec": 1.0},
            cooldown_seconds=0,
        )
        payload = {"latency_ms": 5000, "metadata": {}}
        ae._check_latency(payload)
        assert len(ae.get_recent_alerts()) == 1

    def test_retrieval_quality_check(self, tmp_db, event_bus):
        ae = AlertEngine(
            tmp_db, event_bus,
            thresholds={"min_retrieval_score": 0.5},
            cooldown_seconds=0,
        )
        ae._check_retrieval_quality({"metadata": {"retrieval_score": 0.1}})
        assert len(ae.get_recent_alerts()) == 1

    def test_system_resource_check(self, tmp_db, event_bus):
        ae = AlertEngine(
            tmp_db, event_bus,
            thresholds={"cpu_percent": 50.0, "memory_mb": 100.0},
            cooldown_seconds=0,
        )
        ae._check_system_resources({
            "metadata": {"cpu_percent": 95.0, "ram_used_mb": 200.0}
        })
        # Should produce 2 alerts (CPU + RAM)
        assert len(ae.get_recent_alerts()) == 2

    def test_reset_cooldowns(self, tmp_db):
        ae = AlertEngine(tmp_db, cooldown_seconds=300)
        ae.raise_alert("Test", "WARNING", "msg")
        ae.reset_cooldowns()
        a2 = ae.raise_alert("Test", "WARNING", "msg2")
        assert a2 is not None

    def test_event_bus_publishes_alert(self, tmp_db, event_bus):
        received = []
        event_bus.subscribe("AlertRaised", lambda p: received.append(p))
        ae = AlertEngine(tmp_db, event_bus, cooldown_seconds=0)
        ae.raise_alert("Test", "WARNING", "msg")
        time.sleep(0.2)
        assert len(received) == 1


# =====================================================================
# ReportGenerator Tests
# =====================================================================


class TestReportGenerator:
    def test_generate_daily_report(self, tmp_db, tmp_path):
        dg = DashboardGenerator(tmp_db)
        rg = ReportGenerator(tmp_db, output_dir=tmp_path, dashboard_generator=dg)
        path = rg.generate_daily_report()
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Analytics Report" in content

    def test_generate_weekly_report(self, tmp_db, tmp_path):
        rg = ReportGenerator(tmp_db, output_dir=tmp_path)
        path = rg.generate_weekly_report()
        assert path.exists()

    def test_json_report_also_created(self, tmp_db, tmp_path):
        rg = ReportGenerator(tmp_db, output_dir=tmp_path)
        md_path = rg.generate_daily_report()
        json_path = md_path.with_suffix(".json")
        # The JSON report should exist with the same timestamp prefix
        json_files = list(tmp_path.glob("report_daily_*.json"))
        assert len(json_files) == 1

    def test_report_with_data(self, tmp_db, tmp_path):
        tmp_db.insert_session("s1")
        tmp_db.insert_query_log({
            "query_id": "q1", "session_id": "s1",
            "status": "success", "intent": "fees",
        })
        dg = DashboardGenerator(tmp_db)
        rg = ReportGenerator(tmp_db, output_dir=tmp_path, dashboard_generator=dg)
        path = rg.generate_daily_report()
        content = path.read_text(encoding="utf-8")
        assert "Total Queries" in content


# =====================================================================
# Alert Value Object Tests
# =====================================================================


class TestAlert:
    def test_to_dict(self):
        alert = Alert("HighLatency", "WARNING", "Latency exceeded")
        d = alert.to_dict()
        assert d["alert_type"] == "HighLatency"
        assert d["severity"] == "WARNING"
        assert "alert_id" in d
        assert "timestamp" in d


# =====================================================================
# AnalyticsManager Tests
# =====================================================================


class TestAnalyticsManager:
    def test_init(self, tmp_path):
        cfg = {"database_path": str(tmp_path / "test.db")}
        mgr = AnalyticsManager(config=cfg)
        assert mgr.store is not None
        assert mgr.event_bus is not None

    def test_start_stop(self, tmp_path):
        cfg = {
            "database_path": str(tmp_path / "test.db"),
            "system_monitor_interval_seconds": 60,
        }
        mgr = AnalyticsManager(config=cfg)
        mgr.start()
        time.sleep(0.3)
        mgr.stop()

    def test_track_turn(self, tmp_path):
        cfg = {"database_path": str(tmp_path / "test.db")}
        mgr = AnalyticsManager(config=cfg)
        mgr.start()
        mgr.track_turn({
            "query_id": "q1",
            "session_id": "s1",
            "raw_query": "Test question",
            "status": "success",
        })
        time.sleep(0.5)
        mgr.stop()
        row = mgr.store.fetchone("SELECT * FROM query_logs WHERE query_id = 'q1'")
        assert row is not None

    def test_publish_event(self, tmp_path):
        cfg = {"database_path": str(tmp_path / "test.db")}
        mgr = AnalyticsManager(config=cfg)
        received = []
        mgr.event_bus.subscribe("TestEvent", lambda p: received.append(p))
        mgr.publish_event("TestEvent", {"key": "val"})
        time.sleep(0.2)
        assert len(received) == 1

    def test_get_dashboard(self, tmp_path):
        cfg = {"database_path": str(tmp_path / "test.db")}
        mgr = AnalyticsManager(config=cfg)
        dashboard = mgr.get_dashboard()
        assert "summary" in dashboard

    def test_get_all_stats(self, tmp_path):
        cfg = {"database_path": str(tmp_path / "test.db")}
        mgr = AnalyticsManager(config=cfg)
        stats = mgr.get_all_stats()
        assert "query" in stats
        assert "retrieval" in stats
        assert "conversation" in stats
        assert "knowledge" in stats

    def test_generate_report(self, tmp_path):
        cfg = {
            "database_path": str(tmp_path / "test.db"),
            "report_output_dir": str(tmp_path / "reports"),
        }
        mgr = AnalyticsManager(config=cfg)
        path = mgr.generate_report(hours=1, label="test")
        assert Path(path).exists()
