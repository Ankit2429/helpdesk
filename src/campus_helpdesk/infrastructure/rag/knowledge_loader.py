"""Unified composite KnowledgeLoader adapter for Markdown and PDF documents."""

from pathlib import Path

from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.pdf_loader import PDFKnowledgeLoader


class KnowledgeLoader:
    """Unified document loader supporting Markdown (.md) and PDF (.pdf) knowledge sources."""

    def __init__(self, knowledge_source_path: Path, max_file_size_bytes: int) -> None:
        self._knowledge_source_path = knowledge_source_path
        self._max_file_size_bytes = max_file_size_bytes
        self._pdf_loader = PDFKnowledgeLoader(knowledge_source_path, max_file_size_bytes)
        self._markdown_loader = MarkdownKnowledgeLoader(knowledge_source_path, max_file_size_bytes)

    def load(self, source_path: Path) -> list[KnowledgeDocument]:
        """Delegate loading to the appropriate loader based on file extension."""
        suffix = source_path.suffix.casefold()
        if suffix == ".pdf":
            return self._pdf_loader.load(source_path)
        elif suffix == ".md":
            return self._markdown_loader.load(source_path)
        else:
            raise ValueError(
                f"Unsupported knowledge source extension '{source_path.suffix}'. "
                "Supported extensions: .pdf, .md"
            )
