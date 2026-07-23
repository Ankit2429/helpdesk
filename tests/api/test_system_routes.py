"""Tests for system routes."""

from fastapi.testclient import TestClient

from campus_helpdesk.main import create_app


client = TestClient(create_app())


def test_root_returns_api_identity() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Campus Helpdesk API", "status": "online"}


def test_health_returns_healthy_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
