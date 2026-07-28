"""Markdown Text Cleaning & Standardization Component."""

import re


class MarkdownTextCleaner:
    """Cleans, normalizes, and standardizes raw markdown content."""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
    MULTIPLE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
    TRAILING_WHITESPACE_PATTERN = re.compile(r"[ \t]+$", re.MULTILINE)

    def clean(self, content: str) -> str:
        """Apply sequential cleaning transformations to raw markdown text.

        Returns cleaned, standardized markdown content without frontmatter headers.
        """
        # 1. Strip raw frontmatter if present
        text = self.FRONTMATTER_PATTERN.sub("", content)

        # 2. Normalize Windows CRLF line endings to standard LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Strip noisy HTML tags while preserving line breaks
        text = self.HTML_TAG_PATTERN.sub("", text)

        # 4. Remove trailing whitespace on every line
        text = self.TRAILING_WHITESPACE_PATTERN.sub("", text)

        # 5. Compress multiple blank lines to a maximum of 2 newlines (1 blank line)
        text = self.MULTIPLE_NEWLINES_PATTERN.sub("\n\n", text)

        return text.strip()
