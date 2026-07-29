import logging
import time
import json
import uuid
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("campus_helpdesk.tracer")

class DiagnosticTracer:
    """Thread-safe diagnostic tracer for RAG performance monitoring and retrieval tracing."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DiagnosticTracer, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "logs"):
        if self._initialized:
            return
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.diagnostics_log_path = self.log_dir / "retrieval_diagnostics.jsonl"
        self._initialized = True

    def start_span(self, query: str) -> Dict[str, Any]:
        """Start a trace span for a user request."""
        return {
            "trace_id": str(uuid.uuid4()),
            "query": query,
            "start_time": time.time(),
            "retrieval": {},
            "inference": {}
        }

    def log_retrieval_step(self, span: Dict[str, Any], vector_candidates: List[Dict], bm25_candidates: List[Dict], rrf_output: List[Dict], confidence_score: float, latency_ms: float):
        """Log diagnostic data for the retrieval and ranking phase."""
        span["retrieval"] = {
            "vector_candidates": [c.get("source", "") for c in vector_candidates[:5]],
            "bm25_candidates": [c.get("source", "") for c in bm25_candidates[:5]],
            "rrf_output": [c.get("source", "") for c in rrf_output[:5]],
            "confidence_score": confidence_score,
            "latency_ms": latency_ms
        }
        logger.info(f"Trace {span['trace_id']} - Retrieval Complete: latency={latency_ms:.1f}ms, confidence={confidence_score:.2f}")

    def log_inference_step(self, span: Dict[str, Any], selected_contexts: List[str], answer: str, latency_ms: float):
        """Log diagnostic data for LLM generation."""
        span["inference"] = {
            "selected_contexts": selected_contexts,
            "latency_ms": latency_ms
        }
        total_latency = (time.time() - span["start_time"]) * 1000.0
        logger.info(f"Trace {span['trace_id']} - Inference Complete: latency={latency_ms:.1f}ms, total_latency={total_latency:.1f}ms")
        
        # Write to retrieval_diagnostics.jsonl
        try:
            with open(self.diagnostics_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "trace_id": span["trace_id"],
                    "query": span["query"],
                    "total_latency_ms": total_latency,
                    "retrieval": span["retrieval"],
                    "inference": span["inference"]
                }) + "\n")
        except Exception as e:
            logger.error(f"Failed to write trace log: {e}")

def get_tracer() -> DiagnosticTracer:
    """Return process-wide tracer instance."""
    return DiagnosticTracer()
