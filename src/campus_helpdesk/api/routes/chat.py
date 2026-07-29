"""Chat API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from campus_helpdesk.api.dependencies import get_chat_service
from campus_helpdesk.api.schemas.chat import ChatRequest, ChatResponse
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.application.exceptions import LLMServiceError

router = APIRouter(prefix="/chat", tags=["chat"])


from pydantic import BaseModel

class FeedbackRequest(BaseModel):
    query: str
    reply: str
    helpful: bool
    session_id: str = "default"

@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def chat(
    payload: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Generate a response from the configured local language model."""
    try:
        result = chat_service.respond(payload.message, session_id=payload.session_id)
    except LLMServiceError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error

    return ChatResponse(reply=result.reply, status=result.status)

@router.post("/feedback", status_code=status.HTTP_200_OK)
def feedback(
    payload: FeedbackRequest
):
    """Record user helpfulness feedback for prompt tuning and monitoring."""
    import json
    import os
    feedback_log = "logs/user_feedback.jsonl"
    os.makedirs("logs", exist_ok=True)
    try:
        with open(feedback_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "query": payload.query,
                "reply": payload.reply,
                "helpful": payload.helpful,
                "session_id": payload.session_id
            }) + "\n")
        return {"status": "success", "message": "Feedback recorded."}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to record feedback: {e}")
