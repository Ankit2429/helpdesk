"""Text Cleaner module for stripping noise, duplicate newlines, and boilerplates."""

import re


class TextCleaner:
    """Clean and normalize extracted markdown text."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean markdown text by collapsing extra whitespace and removing control characters."""
        if not text:
            return ""

        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse 3+ consecutive newlines into 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip trailing/leading spaces on each line
        lines = [line.strip() for line in text.split("\n")]
        
        return "\n".join(lines).strip()
