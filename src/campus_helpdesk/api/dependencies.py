"""Dependencies shared by HTTP routes."""

from typing import cast

from fastapi import Request

from campus_helpdesk.application.chat_service import ChatService


def get_chat_service(request: Request) -> ChatService:
    """Retrieve the configured chat service from the application container."""
    return cast(ChatService, request.app.state.chat_service)
