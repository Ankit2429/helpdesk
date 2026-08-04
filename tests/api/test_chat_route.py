"""Tests for the temporary chat route."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from campus_helpdesk.domain.knowledge import KnowledgeDocument, SearchResult
from campus_helpdesk.main import create_app


class FakeLLMService:
    """Test double that avoids a running Ollama instance."""

    def generate(self, prompt: str) -> str:
        return f"Local model response: {prompt}"


def test_chat_returns_model_response() -> None:
    fake_rag = MagicMock()
    fake_rag.search.return_value = [
        SearchResult(
            document=KnowledgeDocument(content="The library is located in Building A.", metadata={}),
            distance=0.2,
        )
    ]
    app = create_app(llm_service=FakeLLMService())
    app.state.chat_service._rag_pipeline = fake_rag

    test_client = TestClient(app)
    response = test_client.post("/chat", json={"message": "Where is the library?"})

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "completed"
    assert "User Question: where is the library" in res_data["reply"]


def test_chat_rejects_blank_message() -> None:
    app = create_app(llm_service=FakeLLMService())
    test_client = TestClient(app)
    response = test_client.post("/chat", json={"message": ""})

    assert response.status_code == 422

