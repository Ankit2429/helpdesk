import pytest
import time
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.services.answerability_engine import AnswerabilityEngine
from campus_helpdesk.services.citation_validator import CitationValidator
from campus_helpdesk.domain.memory.conversation_memory import ConversationMemory
from campus_helpdesk.application.session_manager import SessionManager

def test_sprint3_answerability():
    # Insufficient context
    res = AnswerabilityEngine.evaluate_answerability("What is the fee?", [], "LOW")
    assert res == "Insufficient"
    
    # Partial context
    contexts = [KnowledgeDocument(content="Anti-ragging committee regulations apply to all campuses.", metadata={})]
    res = AnswerabilityEngine.evaluate_answerability("Who is on the Anti-Ragging committee?", contexts, "MEDIUM")
    assert res == "Partial"
    
    # Supported context
    contexts = [KnowledgeDocument(content="The chairperson of the Anti-Ragging committee is Prof. Sanjay Kotabagi.", metadata={})]
    res = AnswerabilityEngine.evaluate_answerability("Who is on the Anti-Ragging committee?", contexts, "HIGH")
    assert res == "Supported"

def test_sprint3_citation_validator():
    contexts = [
        KnowledgeDocument(content="fee details here", metadata={"source_url": "https://www.kletech.ac.in/fees"}),
        KnowledgeDocument(content="anti ragging details here", metadata={"source_url": "https://www.kletech.ac.in/anti-ragging"})
    ]
    
    # Valid citations
    reply = "The fees are listed here [1] and the committee here [2]."
    cleaned = CitationValidator.validate_citations(reply, contexts)
    assert "[1]" in cleaned and "[2]" in cleaned

    # Out of bounds citation
    reply_invalid = "Fees details [3] and committee details [1]."
    cleaned = CitationValidator.validate_citations(reply_invalid, contexts)
    assert "[1]" in cleaned
    assert "[3]" not in cleaned

    # Fabricated URL
    reply_url = "See details at https://www.fabricated-url.com/fake."
    cleaned = CitationValidator.validate_citations(reply_url, contexts)
    assert "https://www.fabricated-url.com/fake" not in cleaned

def test_sprint3_conversation_memory():
    memory = ConversationMemory(max_history_turns=2)
    memory.add_message("user", "hi")
    memory.add_message("assistant", "hello")
    assert len(memory.get_messages()) == 2
    
    # Exceed limit to trigger trim
    memory.add_message("user", "how are you?")
    memory.add_message("assistant", "fine")
    memory.add_message("user", "nice")
    memory.add_message("assistant", "great")
    
    # Max turns is 2 (so max messages is 4)
    assert len(memory.get_messages()) == 4
    assert memory.get_messages()[0]["content"] == "how are you?"

def test_sprint3_session_manager():
    manager = SessionManager(ttl_seconds=1, max_history_turns=2)
    mem = manager.get_or_create_session("session1")
    assert mem is not None
    
    # Retrieve existing
    mem2 = manager.get_or_create_session("session1")
    assert mem is mem2
    
    # Wait for TTL expiration
    time.sleep(1.2)
    manager.cleanup_expired_sessions()
    
    # Check that session1 is cleaned up
    assert "session1" not in manager.sessions
