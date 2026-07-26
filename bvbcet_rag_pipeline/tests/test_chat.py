"""Unit tests for RAGChatEngine and ChatHistoryLogger."""

import json
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch, MagicMock

from langchain_core.documents import Document
from chat import ChatHistoryLogger, RAGChatEngine, PROMPT_TEMPLATE


def test_chat_history_logger():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        log_file = temp_dir / "chat_history.json"
        logger_inst = ChatHistoryLogger(log_file=log_file)

        logger_inst.log_turn(
            question="What is the admission procedure?",
            answer="Apply via KCET or COMEDK.",
            sources=[{"source": "admissions.md", "score": 0.92}],
            metrics={"confidence": 0.92, "search_time_ms": 12.5, "inference_time_s": 0.8},
        )

        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 1
        assert data[0]["question"] == "What is the admission procedure?"
        assert data[0]["answer"] == "Apply via KCET or COMEDK."
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@patch.object(RAGChatEngine, "generate_llm_answer")
def test_rag_chat_engine_ask(mock_llm):
    mock_llm.return_value = ("The KCET quota admissions start in July.", 1.2)

    temp_dir = Path(tempfile.mkdtemp())
    try:
        log_file = temp_dir / "test_history.json"
        persist_dir = temp_dir / "chroma"
        engine = RAGChatEngine(
            llm_model="llama3.1:8b",
            embedding_model="all-MiniLM-L6-v2",
            persist_dir=persist_dir,
            top_k=2,
        )
        engine.history_logger = ChatHistoryLogger(log_file=log_file)

        # Mock retriever response
        dummy_doc = Document(
            page_content="Admissions for KCET quota start in July.",
            metadata={
                "id": "chunk_01",
                "source": "admissions.md",
                "heading": "KCET Quota",
                "category": "admissions",
                "score": 0.95,
            },
        )
        engine.retriever.retrieve = MagicMock(return_value=[dummy_doc])

        result = engine.ask("When do KCET admissions start?")

        assert result["answer"] == "The KCET quota admissions start in July."
        assert len(result["sources"]) == 1
        assert result["metrics"]["confidence"] == 0.95
        assert result["metrics"]["inference_time_s"] == 1.2
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
