"""Chat API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from campus_helpdesk.api.dependencies import get_chat_service
from campus_helpdesk.api.schemas.chat import ChatRequest, ChatResponse
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.exceptions import LLMServiceError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Generate a response from the configured local language model."""
    try:
        result = chat_service.respond(payload.message)
    except LLMServiceError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    return ChatResponse(reply=result.reply, status=result.status)
