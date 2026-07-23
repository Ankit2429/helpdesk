"""Top-level API router composition."""

from fastapi import APIRouter

from campus_helpdesk.api.routes.chat import router as chat_router
from campus_helpdesk.api.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(chat_router)
