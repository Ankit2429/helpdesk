"""Unit tests for PromptBuilder."""

from langchain_core.documents import Document
from conversation.memory import ChatMessage
from llm.prompt_builder import PromptBuilder


def test_prompt_builder_basic():
    builder = PromptBuilder()
    question = "When do KCET admissions start?"
    history = [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi! How can I help?"),
    ]
    retrieved_docs = [
        Document(page_content="Admissions for KCET start in July.", metadata={"heading": "KCET"}),
    ]

    prompt = builder.build_prompt(question, history, retrieved_docs)

    assert "STRICT GROUNDING & CONSTRAINTS" in prompt
    assert "KCET start in July" in prompt
    assert "When do KCET admissions start?" in prompt
    assert "Hi! How can I help?" in prompt
