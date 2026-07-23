"""PDF loading adapter built on LangChain community loaders."""

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from pypdf.errors import PdfReadError

from campus_helpdesk.domain.knowledge import KnowledgeDocument


class PDFKnowledgeLoader:
    """Load each PDF page as a knowledge document."""

    def __init__(self, knowledge_source_path: Path, max_file_size_bytes: int) -> None:
        self._knowledge_source_path = knowledge_source_path
        self._max_file_size_bytes = max_file_size_bytes

    def load(self, source_path: Path) -> list[KnowledgeDocument]:
        """Extract text and source metadata from a PDF file."""
        resolved_source_path, relative_source_path = self._validate_source_path(source_path)
        try:
            documents = PyPDFLoader(str(resolved_source_path)).load()
        except (OSError, PdfReadError, ValueError) as error:
            raise ValueError("The PDF could not be read as an extractable text document.") from error
        knowledge_documents = [
            KnowledgeDocument(
                content=document.page_content,
                metadata={
                    **{str(key): str(value) for key, value in document.metadata.items()},
                    "source": relative_source_path.as_posix(),
                },
            )
            for document in documents
            if document.page_content.strip()
        ]
        if not knowledge_documents:
            raise ValueError("No extractable PDF text was found. OCR is not configured for scanned PDFs.")
        return knowledge_documents

    def _validate_source_path(self, source_path: Path) -> tuple[Path, Path]:
        """Allow only existing PDF files contained by the configured knowledge directory."""
        if source_path.suffix.casefold() != ".pdf":
            raise ValueError("Only PDF files are supported for knowledge ingestion.")

        source_root = self._knowledge_source_path.resolve()
        try:
            resolved_source_path = source_path.resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError("Knowledge source file does not exist.") from error
        if not resolved_source_path.is_file():
            raise ValueError("Knowledge source path must identify a file.")
        if resolved_source_path.stat().st_size > self._max_file_size_bytes:
            raise ValueError("Knowledge source file exceeds the configured maximum file size.")

        try:
            relative_source_path = resolved_source_path.relative_to(source_root)
        except ValueError as error:
            raise ValueError("Knowledge source must be inside the configured knowledge directory.") from error

        return resolved_source_path, relative_source_path
