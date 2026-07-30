import uuid
import time
from datetime import datetime
from typing import Dict, Any

class PipelineTrace:
    """Utility class for creating and handling trace IDs and event payloads.

    Each turn in the conversation receives a unique ``trace_id`` (UUID v4). The
    trace metadata is stored in the ``pipeline_traces`` table via ``MetricsStore``.
    ``event_payload`` creates a standard dictionary that all analytics modules
    expect when publishing events on the :class:`EventBus`.
    """

    @staticmethod
    def new_trace_id() -> str:
        """Generate a new UUIDv4 string for a pipeline turn."""
        return str(uuid.uuid4())

    @staticmethod
    def event_payload(
        *,
        trace_id: str,
        session_id: str = None,
        turn_id: str = None,
        component: str,
        event_type: str,
        latency_ms: float = None,
        metadata: Dict[str, Any] = None,
        severity: str = "INFO",
    ) -> Dict[str, Any]:
        """Create a normalized payload for an analytics event.

        Parameters
        ----------
        trace_id: str
            The unique identifier for the pipeline turn.
        session_id: str, optional
            The conversation session identifier.
        turn_id: str, optional
            Identifier for the specific turn within a session.
        component: str
            Name of the component emitting the event (e.g., ``Retriever``).
        event_type: str
            Semantic name of the event (e.g., ``QueryReceived``).
        latency_ms: float, optional
            Measured latency for the component, in milliseconds.
        metadata: dict, optional
            Additional free‑form data to store alongside the event.
        severity: str, default ``INFO``
            Log severity – ``INFO``, ``WARNING``, ``ERROR``.
        """
        return {
            "trace_id": trace_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
            "component": component,
            "event_type": event_type,
            "latency_ms": latency_ms,
            "metadata": metadata or {},
            "severity": severity,
        }
