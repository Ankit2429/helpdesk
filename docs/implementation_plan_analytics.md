# Observability & Analytics System Implementation Plan

## 1. Architecture Overview

```mermaid
flowchart TD
    subgraph AppPipeline[RAG / Conversation Pipeline]
        CM[ConversationManager]
        RAG[RAGPipeline]
        VAL[ResponseValidator]
    end

    subgraph Analytics[Analytics & Observability System]
        AM[AnalyticsManager]
        MS[MetricsStore (SQLite)]
        QA[QueryAnalytics]
        RA[RetrievalAnalytics]
        CA[ConversationAnalytics]
        KA[KnowledgeAnalytics]
        PM[PerformanceMonitor]
        QM[QualityMonitor]
        DG[DashboardGenerator]
        RG[ReportGenerator]
    end

    subgraph Storage[Offline Export]
        JSON[JSON Exports]
        CSV[CSV Exports]
        MD[Markdown Reports]
    end

    %% Data collection flow
    CM -->|Log Turn Data| AM
    RAG -->|Log Retrieval Metrics| AM
    VAL -->|Log Validation Status| AM

    %% Internal routing
    AM -->|Process & Write| MS
    MS --> QA
    MS --> RA
    MS --> CA
    MS --> KA
    MS --> PM
    MS --> QM

    %% Reporting & Visualization
    QA & RA & CA & KA & PM & QM --> DG & RG
    DG -->|Local HTML| Storage
    RG -->|MD Reports / CSV| Storage
```

## 2. Component Descriptions

| Component | Responsibility |
|-----------|-----------------|
| **AnalyticsManager** | The orchestrator. Exposes unified APIs (e.g., `track_turn(turn_data)`) to other packages and dispatches metrics asynchronously to prevent request blocking. |
| **MetricsStore** | Lightweight SQLite backend that persists logs. Designed with high-performance inserts, simple schemas, and configurable data retention (automatic pruning of old entries). |
| **QueryAnalytics** | Queries `MetricsStore` to aggregate total queries, query status (success, fallback, failed), hourly/daily trends, and classification categories. |
| **RetrievalAnalytics** | Analyzes document/chunk access frequencies, identifies unused or stale documents, tracks retrieval confidence, and analyzes Cross-Encoder ranking shifts. |
| **ConversationAnalytics** | Tracks session durations, average conversation lengths (in turns), topic shifts, and follow-up query frequencies. |
| **PerformanceMonitor** | Tracks CPU/RAM utilization alongside step-by-step pipeline latency (Query Understanding, Retrieval, Reranking, LLM, Validation). |
| **QualityMonitor** | Evaluates safety parameters: confidence distribution, hallucination flags, citation coverage, and percentage of statements removed. |
| **DashboardGenerator** | Rebuilds a local, highly-optimized responsive HTML dashboard summarizing the health, latency, quality, and usage statistics of the system. |
| **ReportGenerator** | Periodically packages metrics into daily, weekly, and monthly reports formatted as markdown and CSV. |

## 3. Data Flow
1. **Pipeline Execution**: The user asks a question. Each layer tracks its metrics (latencies, inputs, outputs, flags).
2. **Turn Completion**: `ConversationManager` calls `analytics_manager.track_turn(turn_metadata)`.
3. **Database Write**: `AnalyticsManager` writes the turn details to the local SQLite database asynchronously.
4. **On-demand aggregation**: The dashboard or reports call specific analytics components (`QueryAnalytics`, `PerformanceMonitor`, etc.) to run quick aggregations.
5. **Periodic Exports**: Background timer exports aggregated data to JSON/CSV and regenerates the HTML dashboard.

## 4. Database Schema (SQLite)
```sql
CREATE TABLE sessions (
    session_id          TEXT PRIMARY KEY,
    start_time          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time            TIMESTAMP,
    turns_count         INTEGER DEFAULT 0
);

CREATE TABLE query_logs (
    query_id            TEXT PRIMARY KEY,
    session_id          TEXT REFERENCES sessions(session_id),
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_query           TEXT,
    resolved_query      TEXT,
    intent              TEXT,
    status              TEXT CHECK (status IN ('success', 'fallback', 'failed')),
    has_followup        BOOLEAN,
    topic_switched      BOOLEAN
);

CREATE TABLE retrieval_logs (
    query_id            TEXT REFERENCES query_logs(query_id),
    retrieved_chunk_ids TEXT, -- JSON array
    retrieval_score     REAL,
    cross_encoder_score REAL,
    unused_docs_count   INTEGER
);

CREATE TABLE latency_logs (
    query_id            TEXT REFERENCES query_logs(query_id),
    query_understanding REAL,
    retrieval           REAL,
    reranking           REAL,
    llm_generation      REAL,
    validation          REAL,
    end_to_end          REAL
);

CREATE TABLE quality_logs (
    query_id            TEXT REFERENCES query_logs(query_id),
    confidence_score    REAL,
    hallucination_flag  BOOLEAN,
    citation_coverage   REAL,
    unsupported_rate    REAL
);

CREATE TABLE system_metrics (
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent         REAL,
    ram_used_mb         REAL
);
```

## 5. Configuration File (`config/analytics.yaml`)
```yaml
database_path: "data/analytics/metrics.sqlite"
export_directory: "data/analytics/exports"
retention_days: 30
aggregation_interval_minutes: 60
system_monitor_interval_seconds: 10
export_formats:
  - "json"
  - "csv"
  - "html"
latency_thresholds_ms:
  warning: 1500
  critical: 3000
```

## 6. Integration Points
- **`rag_pipeline.py` & `conversation_manager.py`**: Inject a decorator or a straight call to `analytics_manager.track_turn` right before returning the final response.
- **Initialization**: Instantiate `AnalyticsManager` and start the low-priority background threads (system metrics polling, database pruning) on application startup.

## 7. Raspberry Pi 5 Optimization Notes
- **Threaded Metrics Injection**: Writing to SQLite runs on a separate worker thread using a queue to ensure no impact on user query response times.
- **Pruning**: Periodically runs `DELETE FROM ... WHERE timestamp < datetime('now', '-30 days')` followed by a `VACUUM` to limit SSD writes and storage bloat.
- **Local HTML Dashboard**: Completely static HTML/CSS files are written directly to disk. No running web server (like Flask) is active, saving idle CPU cycles.

---
*Please approve this implementation plan or suggest adjustments.*
