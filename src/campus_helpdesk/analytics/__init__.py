"""Analytics package for Campus Helpdesk AI.

Provides:
- AnalyticsManager: central orchestrator wiring all subsystems
- MetricsStore: thread-safe SQLite persistence
- EventBus: lightweight pub/sub for analytics events
- PipelineTrace: trace ID and payload generation
- QueryAnalytics: intent/status/follow-up tracking
- RetrievalAnalytics: retrieval quality indicators
- ConversationAnalytics: session lifecycle metrics
- KnowledgeAnalytics: document access patterns & knowledge gaps
- PerformanceMonitor: background CPU/RAM monitoring
- DashboardGenerator: structured dashboard payloads
- AlertEngine: threshold-based alerting with cooldown
- ReportGenerator: Markdown/JSON report production
"""

from campus_helpdesk.analytics.alert_engine import AlertEngine
from campus_helpdesk.analytics.analytics_manager import AnalyticsManager
from campus_helpdesk.analytics.conversation_analytics import ConversationAnalytics
from campus_helpdesk.analytics.dashboard_generator import DashboardGenerator
from campus_helpdesk.analytics.event_bus import EventBus
from campus_helpdesk.analytics.knowledge_analytics import KnowledgeAnalytics
from campus_helpdesk.analytics.metrics_store import MetricsStore
from campus_helpdesk.analytics.performance_monitor import PerformanceMonitor
from campus_helpdesk.analytics.pipeline_trace import PipelineTrace
from campus_helpdesk.analytics.query_analytics import QueryAnalytics
from campus_helpdesk.analytics.report_generator import ReportGenerator
from campus_helpdesk.analytics.retrieval_analytics import RetrievalAnalytics

__all__ = [
    "AlertEngine",
    "AnalyticsManager",
    "ConversationAnalytics",
    "DashboardGenerator",
    "EventBus",
    "KnowledgeAnalytics",
    "MetricsStore",
    "PerformanceMonitor",
    "PipelineTrace",
    "QueryAnalytics",
    "ReportGenerator",
    "RetrievalAnalytics",
]

