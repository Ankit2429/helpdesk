"""Knowledge Base folder creation and management module."""

from pathlib import Path
from config.categories import CATEGORIES
from config.config import LOGS_DIR, MARKDOWN_DIR, METADATA_DIR, PDF_DIR


class FolderManager:
    """Manages creation and verification of knowledge base folder structures."""

    @staticmethod
    def initialize_structure() -> None:
        """Create all 18 category markdown folders, pdf, metadata, and log directories."""
        for category in CATEGORIES:
            (MARKDOWN_DIR / category).mkdir(parents=True, exist_ok=True)

        PDF_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_category_path(category: str) -> Path:
        """Get output directory for a target category."""
        target = MARKDOWN_DIR / category
        target.mkdir(parents=True, exist_ok=True)
        return target
