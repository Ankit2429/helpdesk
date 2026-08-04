"""Domain entities for multi-turn conversation memory."""

import datetime
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """Single message in conversation history."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())


@dataclass
class ConversationSession:
    """Active multi-turn chat session with history trimming and reset support."""

    session_id: str = "default"
    messages: list[ChatMessage] = field(default_factory=list)
