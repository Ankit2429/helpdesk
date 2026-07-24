"""Chat service protocol boundary."""

from typing import Protocol

from campus_helpdesk.application.chat_models import ChatResult


class ChatService(Protocol):
    """Application contract for responding to a chat request."""

    def respond(self, message: str) -> ChatResult:
        """Produce a response for a validated chat request."""

