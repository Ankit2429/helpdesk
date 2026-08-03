"""Regression test verifying a single unified production knowledge pipeline."""

from pathlib import Path

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline


def test_production_settings_knowledge_path():
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.knowledge_source_path == Path("archive/bvbcet_scraper/knowledge_base/markdown")


def test_single_production_pipeline_retrieval():
    settings = get_settings()
    pipeline = create_rag_pipeline(settings)

    results = pipeline.search("Where is the Central Library located?")
    assert len(results) > 0

    sources = [res.document.metadata.get("source", "") for res in results]
    # Ensure all retrieved sources come from canonical markdown files
    for source in sources:
        assert not source.endswith(".pdf") or "data/knowledge" not in source
