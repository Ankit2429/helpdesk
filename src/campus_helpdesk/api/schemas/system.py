"""System endpoint response schemas."""

from pydantic import BaseModel


class RootResponse(BaseModel):
    """API identity response."""

    message: str
    status: str


class HealthResponse(BaseModel):
    """Service health status including component diagnostics."""

    status: str
    components: dict[str, str]
    disk_space: dict[str, float | str]
    memory: dict[str, float | str]
