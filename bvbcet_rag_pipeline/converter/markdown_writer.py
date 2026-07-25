"""Markdown Writer module for saving Markdown files to knowledge_base categories."""

from pathlib import Path
from storage.folder_manager import FolderManager


class MarkdownWriter:
    """Formats and writes Markdown files into target category directories."""

    @staticmethod
    def write_markdown(category: str, filename_stem: str, content: str) -> Path:
        """Write content string to target category Markdown file."""
        output_dir = FolderManager.get_category_path(category)
        output_file = output_dir / f"{filename_stem}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

        return output_file
