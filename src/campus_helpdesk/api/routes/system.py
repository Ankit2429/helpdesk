"""System and service-status routes."""

from fastapi import APIRouter

from campus_helpdesk.api.schemas.system import HealthResponse, RootResponse

router = APIRouter(tags=["system"])


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    """Return the API identity and current implementation status."""
    return RootResponse(message="Campus Helpdesk API", status="online")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a lightweight process health status."""
    return HealthResponse(status="healthy")
