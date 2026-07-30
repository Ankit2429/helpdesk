"""Markdown Document Reader Module.

Parses Markdown files from the knowledge base directory, extracting metadata,
titles, hierarchical headings, and section text blocks into structured data objects.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SectionBlock:
    """Represents a single section in a Markdown document."""

    heading: str
    level: int
    content: str
    word_count: int


@dataclass
class MarkdownDocument:
    """Structured representation of a parsed Markdown file."""

    path: Path
    filename: str
    title: str
    headings: List[str]
    sections: List[SectionBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_word_count: int = 0
    raw_content: str = ""


class MarkdownReader:
    """Reads and parses Markdown documents from disk."""

    def __init__(self, input_dir: Path):
        self.input_dir = Path(input_dir)

    def find_all_markdown_files(self) -> List[Path]:
        """Discovers all `.md` files recursively under input_dir."""
        if not self.input_dir.exists():
            logger.error(f"Input directory does not exist: {self.input_dir}")
            return []
        
        md_files = [p for p in self.input_dir.rglob("*.md") if p.is_file()]
        logger.info(f"Discovered {len(md_files)} markdown files in {self.input_dir}")
        return sorted(md_files)

    def parse_file(self, file_path: Path) -> Optional[MarkdownDocument]:
        """Parses a single Markdown file into a MarkdownDocument object.

        Args:
            file_path: Absolute or relative Path to target `.md` file.

        Returns:
            MarkdownDocument instance or None if unparseable/empty.
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_content = f.read().strip()

            if not raw_content:
                logger.warning(f"Skipping empty markdown file: {file_path.name}")
                return None

            lines = raw_content.splitlines()

            # Extract title (first # Heading or filename)
            title = file_path.stem.replace("_", " ").title()
            for line in lines:
                if line.startswith("# "):
                    title = line.lstrip("#").strip()
                    break

            # Parse section blocks by headings (#, ##, ###, ####)
            sections: List[SectionBlock] = []
            headings: List[str] = []
            current_heading = title
            current_level = 1
            current_lines: List[str] = []

            heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

            for line in lines:
                match = heading_pattern.match(line)
                if match:
                    # Save previous section block if it contains content
                    if current_lines:
                        block_content = "\n".join(current_lines).strip()
                        if block_content:
                            w_count = len(block_content.split())
                            sections.append(
                                SectionBlock(
                                    heading=current_heading,
                                    level=current_level,
                                    content=block_content,
                                    word_count=w_count,
                                )
                            )
                        current_lines = []

                    current_level = len(match.group(1))
                    current_heading = match.group(2).strip()
                    headings.append(current_heading)
                else:
                    current_lines.append(line)

            # Flush remaining section lines
            if current_lines:
                block_content = "\n".join(current_lines).strip()
                if block_content:
                    w_count = len(block_content.split())
                    sections.append(
                        SectionBlock(
                            heading=current_heading,
                            level=current_level,
                            content=block_content,
                            word_count=w_count,
                        )
                    )

            total_words = sum(s.word_count for s in sections)

            return MarkdownDocument(
                path=file_path,
                filename=file_path.name,
                title=title,
                headings=headings,
                sections=sections,
                metadata={"relative_path": str(file_path.relative_to(self.input_dir) if self.input_dir in file_path.parents else file_path.name)},
                total_word_count=total_words,
                raw_content=raw_content,
            )

        except Exception as e:
            logger.error(f"Failed to read/parse markdown file {file_path}: {e}")
            return None
