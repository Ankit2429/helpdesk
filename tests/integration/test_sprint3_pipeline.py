import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from campus_helpdesk.main import create_app
from campus_helpdesk.application.chat_models import ChatResult
from campus_helpdesk.application.chat_service import ChatService
from campus_helpdesk.config.settings import get_settings

def test_sprint3_api_health_ready():
    app = create_app()
    client = TestClient(app)
    
    # Test GET /health
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded"]
    
    # Test GET /ready
    response = client.get("/ready")
    assert response.status_code in [200, 503]

def test_sprint3_chat_feedback_flow():
    app = create_app()
    client = TestClient(app)
    
    # Test POST /chat/feedback
    response = client.post("/chat/feedback", json={
        "query": "Is there a library?",
        "reply": "Yes, there is [1].",
        "helpful": True,
        "session_id": "test_sess"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_sprint3_chat_service_mocked_llm():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "The COMEDK fee is Rs. 3,04,100 per annum [1]."
    
    app = create_app(llm_service=mock_llm)
    client = TestClient(app)
    
    # Test POST /chat
    response = client.post("/chat", json={
        "message": "What is the CSE COMEDK fee?",
        "session_id": "test_user_session"
    })
    assert response.status_code == 200
    assert "COMEDK fee" in response.json()["reply"]
