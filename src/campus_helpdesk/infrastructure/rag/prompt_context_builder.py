"""Structured Prompt Context Builder for RAG retrieval."""

import hashlib
from collections.abc import Sequence

from campus_helpdesk.domain.knowledge import SearchResult


class PromptContextBuilder:
    """Formats retrieved KnowledgeDocument chunks into structured prompt context with citations."""

    def __init__(
        self,
        max_context_size: int = 3000,
        similarity_threshold: float = 2.0,
    ) -> None:
        self.max_context_size = max_context_size
        self.similarity_threshold = similarity_threshold

    def build_context(self, search_results: Sequence[SearchResult]) -> str:
        """Filter by similarity threshold, deduplicate, format citations, and enforce max_context_size."""
        if not search_results:
            return ""

        seen_hashes: set[str] = set()
        formatted_chunks: list[str] = []
        current_char_count = 0

        for match in search_results:
            if match.distance > self.similarity_threshold:
                continue

            doc = match.document
            doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
            if doc_hash in seen_hashes:
                continue
            seen_hashes.add(doc_hash)

            # Metadata formatting
            source = doc.metadata.get("source", "Knowledge Base")
            title = doc.metadata.get("title", doc.metadata.get("Header 1", "Campus Guide"))
            section = doc.metadata.get(
                "Header 2",
                doc.metadata.get("Header 3", doc.metadata.get("category", "")),
            )

            header_parts = [f"Source: {source}"]
            if title and title != ".":
                header_parts.append(f"Title: {title}")
            if section and section != ".":
                header_parts.append(f"Section: {section}")

            meta_header = f"[{' | '.join(header_parts)}]"
            block = f"{meta_header}\n{doc.content.strip()}"

            if current_char_count + len(block) > self.max_context_size:
                if not formatted_chunks:
                    # Include at least one block truncated if single block exceeds size
                    formatted_chunks.append(block[: self.max_context_size])
                break

            formatted_chunks.append(block)
            current_char_count += len(block)

        return "\n\n---\n\n".join(formatted_chunks)
