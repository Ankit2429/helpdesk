"""Knowledge Normalization Pipeline Orchestrator."""

import logging
from pathlib import Path
from typing import Any

from campus_helpdesk.infrastructure.knowledge.duplicate_detector import DuplicateDetector
from campus_helpdesk.infrastructure.knowledge.metadata_extractor import MetadataExtractor
from campus_helpdesk.infrastructure.knowledge.text_cleaner import MarkdownTextCleaner

logger = logging.getLogger(__name__)


class KnowledgeNormalizationPipeline:
    """Orchestrates metadata extraction, text cleaning, duplicate detection, and canonical output."""

    def __init__(
        self,
        raw_dir: Path | str = "data/raw",
        canonical_dir: Path | str = "data/canonical_markdown",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.canonical_dir = Path(canonical_dir)
        self.cleaner = MarkdownTextCleaner()
        self.metadata_extractor = MetadataExtractor()
        self.duplicate_detector = DuplicateDetector()

    def process_file(self, source_path: Path) -> Path | None:
        """Process a single raw markdown file into canonical format.

        Returns output canonical file path, or None if skipped (e.g. duplicate).
        """
        try:
            raw_content = source_path.read_text(encoding="utf-8")
        except Exception as err:
            logger.warning("Failed to read raw file %s: %s", source_path, err)
            return None

        # 1. Clean markdown content
        cleaned_body = self.cleaner.clean(raw_content)

        # 2. Check for duplicate content
        if self.duplicate_detector.is_duplicate(cleaned_body):
            logger.info("Skipping duplicate content in %s", source_path)
            return None

        self.duplicate_detector.register(cleaned_body)

        # 3. Extract & infer metadata
        metadata = self.metadata_extractor.extract(raw_content, source_path=source_path)

        # 4. Format canonical markdown output
        frontmatter = self.metadata_extractor.format_frontmatter(metadata)
        canonical_content = f"{frontmatter}\n{cleaned_body}\n"

        # 5. Write to canonical destination
        relative_path = source_path.name
        output_path = self.canonical_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(canonical_content, encoding="utf-8")

        return output_path

    def run(self) -> dict[str, Any]:
        """Execute normalization across all markdown files in raw_dir."""
        return self.process_directory(self.raw_dir)
    def process_directory(self, input_dir: Path | None = None) -> dict[str, Any]:
        """Process all markdown files in the specified input directory (defaults to self.raw_dir)."""
        source_dir = input_dir or self.raw_dir
        self.canonical_dir.mkdir(parents=True, exist_ok=True)

        md_files = list(source_dir.rglob("*.md"))
        processed_count = 0
        duplicate_count = 0
        output_paths: list[Path] = []

        for source_file in md_files:
            output_file = self.process_file(source_file)
            if output_file:
                processed_count += 1
                output_paths.append(output_file)
            else:
                duplicate_count += 1

        summary = {
            "total_files_scanned": len(md_files),
            "canonical_processed": processed_count,
            "duplicates_skipped": duplicate_count,
            "output_directory": str(self.canonical_dir),
        }
        logger.info("Normalization Pipeline complete: %s", summary)
        return summary
