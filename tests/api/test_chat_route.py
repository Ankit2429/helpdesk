"""Tests for the temporary chat route."""

from fastapi.testclient import TestClient

from campus_helpdesk.main import create_app


class FakeLLMService:
    """Test double that avoids a running Ollama instance."""

    def generate(self, prompt: str) -> str:
        return f"Local model response: {prompt}"


client = TestClient(create_app(llm_service=FakeLLMService()))


def test_chat_returns_model_response() -> None:
    response = client.post("/chat", json={"message": "Where is the library?"})

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Local model response: Where is the library?",
        "status": "completed",
    }


def test_chat_rejects_blank_message() -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422
