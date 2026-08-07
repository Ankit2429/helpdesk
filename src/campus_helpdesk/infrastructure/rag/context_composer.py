"""Context Composer for RAG search result deduplication and passage merging."""

import difflib
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.domain.knowledge import SearchResult

logger = logging.getLogger(__name__)


class ContextComposer:
    """Deduplicates near-identical RAG search chunks and merges candidate passages within context limits."""

    def __init__(
        self,
        enable_composer: bool = True,
        dedup_threshold: float = 0.85,
        max_context_size: int = 7000,
        settings: Settings | None = None,
    ) -> None:
        """Initialize ContextComposer with deduplication threshold and budget constraints.

        Args:
            enable_composer: Feature flag to toggle composer deduplication.
            dedup_threshold: Text similarity ratio threshold (0.0 - 1.0) above which chunks are considered duplicates.
            max_context_size: Maximum total character count for composed context.
            settings: Optional Settings instance.
        """
        if settings is not None:
            self.enable_composer = getattr(settings, "enable_context_composer", True)
            self.dedup_threshold = getattr(settings, "context_composer_dedup_threshold", 0.85)
            self.max_context_size = getattr(settings, "context_composer_max_context_size", 3500)
        else:
            self.enable_composer = enable_composer
            self.dedup_threshold = dedup_threshold
            self.max_context_size = max_context_size

    def compose(self, search_results: Sequence[SearchResult]) -> list[SearchResult]:
        """Deduplicate `-dup` file pairs and text-similar chunks, preserving citations and context limits.

        Args:
            search_results: Ordered list of SearchResult objects from retriever/reranker.

        Returns:
            Filtered list of SearchResult objects with duplicates removed.
        """
        if not self.enable_composer or not search_results:
            return list(search_results)

        # 1. Identify canonical non-dup filenames present in the search results
        canonical_file_map: dict[str, str] = {}  # normalized_base -> actual_non_dup_filename
        for match in search_results:
            src = self._get_source_filename(match)
            if src and not self._is_dup_filename(src):
                base_norm = self._normalize_filename(src)
                canonical_file_map[base_norm] = src

        composed_results: list[SearchResult] = []
        accepted_contents: list[str] = []
        total_chars = 0

        for match in search_results:
            src = self._get_source_filename(match)
            content = match.document.content.strip()

            # Rule 1: Collapse '-dup' files if the non-'-dup' canonical version is present in the set
            if src and self._is_dup_filename(src):
                base_norm = self._normalize_filename(src)
                if base_norm in canonical_file_map:
                    logger.debug(f"ContextComposer: Collapsing duplicate file '{src}' in favor of canonical '{canonical_file_map[base_norm]}'.")
                    continue

            # Rule 2: Content similarity deduplication check
            is_duplicate = False
            for accepted_text in accepted_contents:
                sim = self._calculate_similarity(content, accepted_text)
                if sim >= self.dedup_threshold:
                    logger.debug(f"ContextComposer: Suppressing duplicate chunk (similarity={sim:.2f} >= {self.dedup_threshold}).")
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # Rule 3: Enforce context size budget
            chunk_length = len(content)
            if total_chars + chunk_length > self.max_context_size and composed_results:
                logger.debug(f"ContextComposer: Budget reached ({total_chars} chars). Truncating further search results.")
                break

            composed_results.append(match)
            accepted_contents.append(content)
            total_chars += chunk_length

        return composed_results

    def _get_source_filename(self, match: Any) -> str:
        """Extract source filename from KnowledgeDocument metadata."""
        doc = getattr(match, "document", match)
        meta = getattr(doc, "metadata", {})
        src = meta.get("source") or meta.get("source_filename") or meta.get("parent_document") or ""
        return Path(src).name

    def _is_dup_filename(self, filename: str) -> bool:
        """Check if filename contains '-dup' suffix before extension."""
        name = Path(filename).stem.lower()
        return name.endswith("-dup") or "-dup-" in name

    def _normalize_filename(self, filename: str) -> str:
        """Strip '-dup' suffix and return normalized lower-case base name."""
        stem = Path(filename).stem.lower()
        if stem.endswith("-dup"):
            stem = stem[:-4]
        return stem.replace("-dup-", "-")

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate SequenceMatcher similarity ratio between two text blocks."""
        if text1 == text2:
            return 1.0
        # Fast length ratio check
        len1, len2 = len(text1), len(text2)
        if len1 == 0 or len2 == 0:
            return 0.0
        if min(len1, len2) / max(len1, len2) < 0.6:
            return 0.0

        matcher = difflib.SequenceMatcher(None, text1, text2)
        return matcher.ratio()
