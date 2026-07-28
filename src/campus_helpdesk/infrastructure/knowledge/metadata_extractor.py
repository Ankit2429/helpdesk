"""Metadata Extraction Component for Knowledge Base Normalization."""

import datetime
import hashlib
import re
from pathlib import Path
from typing import Any


class MetadataExtractor:
    """Extracts, parses, and normalizes document metadata into structured frontmatter."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    HEADING_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

    def extract(self, content: str, source_path: Path | None = None) -> dict[str, Any]:
        """Extract existing frontmatter and infer missing metadata fields.

        Returns a dictionary of standardized metadata attributes.
        """
        metadata: dict[str, Any] = {}
        body = content

        # Check for existing YAML frontmatter
        match = self.FRONTMATTER_PATTERN.match(content)
        if match:
            frontmatter_text = match.group(1)
            body = content[match.end():]
            for line in frontmatter_text.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    metadata[key.strip()] = value.strip().strip('"').strip("'")

        # Infer Title if missing
        if "title" not in metadata or not metadata["title"]:
            title_match = self.HEADING_PATTERN.search(body)
            if title_match:
                metadata["title"] = title_match.group(1).strip()
            elif source_path:
                metadata["title"] = source_path.stem.replace("_", " ").replace("-", " ").title()
            else:
                metadata["title"] = "Untitled Document"

        # Infer Category if missing
        if "category" not in metadata or not metadata["category"]:
            if source_path and source_path.parent and source_path.parent.name:
                metadata["category"] = source_path.parent.name
            else:
                metadata["category"] = "general"

        # Structural & Cryptographic Attributes
        clean_text = body.strip()
        metadata["word_count"] = len(clean_text.split())
        metadata["sha256"] = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        metadata["processed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if source_path:
            metadata["source_filename"] = source_path.name

        return metadata

    def format_frontmatter(self, metadata: dict[str, Any]) -> str:
        """Format a metadata dictionary as a standardized YAML frontmatter header."""
        lines = ["---"]
        for key, value in sorted(metadata.items()):
            lines.append(f"{key}: {value}")
        lines.append("---\n")
        return "\n".join(lines)
