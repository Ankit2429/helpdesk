"""Markdown loading adapter supporting YAML frontmatter parsing."""

from pathlib import Path

from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.knowledge.metadata_extractor import MetadataExtractor


class MarkdownKnowledgeLoader:
    """Load Markdown documents into framework-independent KnowledgeDocument objects."""

    def __init__(self, knowledge_source_path: Path, max_file_size_bytes: int) -> None:
        self._knowledge_source_path = knowledge_source_path
        self._max_file_size_bytes = max_file_size_bytes
        self._metadata_extractor = MetadataExtractor()

    def load(self, source_path: Path) -> list[KnowledgeDocument]:
        """Extract text and metadata from a Markdown file."""
        resolved_source_path, relative_source_path = self._validate_source_path(source_path)
        try:
            content = resolved_source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError("The Markdown file could not be read as text.") from error

        metadata_dict = self._metadata_extractor.extract(content, source_path=relative_source_path)

        # Remove raw frontmatter header from body content for vector search indexing
        body_text = self._metadata_extractor.FRONTMATTER_PATTERN.sub("", content).strip()
        if not body_text:
            raise ValueError("No extractable Markdown body text was found.")

        doc_metadata = {
            **{str(k): str(v) for k, v in metadata_dict.items()},
            "source": relative_source_path.as_posix(),
        }

        return [KnowledgeDocument(content=body_text, metadata=doc_metadata)]

    def _validate_source_path(self, source_path: Path) -> tuple[Path, Path]:
        """Allow existing Markdown files contained by the configured knowledge directory."""
        if source_path.suffix.casefold() != ".md":
            raise ValueError("Only Markdown files (.md) are supported by MarkdownKnowledgeLoader.")

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
        except ValueError:
            # Fall back to file stem/name if outside root
            relative_source_path = Path(resolved_source_path.name)

        return resolved_source_path, relative_source_path
