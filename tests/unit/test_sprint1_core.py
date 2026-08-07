import pytest
import os
from pathlib import Path
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.logging.tracer import get_tracer
from campus_helpdesk.infrastructure.loaders.kb_loader import KBLoader
from campus_helpdesk.services.metadata_manager import MetadataManager
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

def test_sprint1_config_and_settings():
    settings = get_settings()
    assert settings.app_name == "Campus Helpdesk"
    assert settings.rag_search_limit >= 1

def test_sprint1_tracer():
    tracer = get_tracer()
    span = tracer.start_span("test query")
    assert span["query"] == "test query"
    assert "trace_id" in span
    
    tracer.log_retrieval_step(span, [{"source": "doc1"}], [{"source": "doc2"}], [{"source": "doc3"}], 0.85, 15.0)
    assert span["retrieval"]["confidence_score"] == 0.85
    assert span["retrieval"]["latency_ms"] == 15.0

def test_sprint1_kb_loader_and_metadata():
    # Test valid metadata validation
    meta = {
        "title": "Test Title",
        "category": "02-academics",
        "document_type": "curriculum",
        "entity_type": "program",
        "department": "Civil Engineering",
        "campus_scope": "Hubballi"
    }
    warnings = MetadataManager.validate(meta)
    assert len(warnings) == 0

    # Test invalid category validation warning
    invalid_meta = {
        "document_type": "invalid-type",
        "department": "Invalid Department"
    }
    warnings = MetadataManager.validate(invalid_meta)
    assert len(warnings) > 0
