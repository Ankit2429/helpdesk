"""Temporary chat service boundary for Phase 1."""

from typing import Protocol

from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.llm_service import LLMService


class ChatService(Protocol):
    """Application contract for responding to a chat request."""

    def respond(self, message: str) -> ChatResult:
        """Produce a response for a validated chat request."""


class DefaultChatService:
    """Delegates chat requests to the configured language model service."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    def respond(self, message: str) -> ChatResult:
        """Generate a direct response without retrieval augmentation."""
        reply = self._llm_service.generate(message)
        return ChatResult(
            reply=reply,
            status="completed",
        )
