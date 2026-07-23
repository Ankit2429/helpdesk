"""System endpoint response schemas."""

from pydantic import BaseModel


class RootResponse(BaseModel):
    """API identity response."""

    message: str
    status: str


class HealthResponse(BaseModel):
    """Basic service health response."""

    status: str
