"""Application-level chat data structures."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ChatResult:
    """A response produced by the chat application service with confidence and evidence diagnostics."""

    reply: str
    status: str = "completed"
    confidence_score: float = 1.0
    confidence_level: str = "HIGH"
    supporting_sources: list[str] = field(default_factory=list)
    retrieval_statistics: dict[str, Any] = field(default_factory=dict)
