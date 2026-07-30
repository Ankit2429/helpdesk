"""Verbatim Citation & Multi-Source Traceability Formatter.

Formats source document citations, attaches verbatim chunk text snippets,
maps multi-source attribution, and calculates confidence scores.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional

from logger.logger import get_logger

logger = get_logger("citation_formatter")


@dataclass
class Citation:
    """Dataclass representing a single source citation."""

    citation_id: int
    source_doc: str
    relative_path: str
    heading: str
    heading_level: int
    page_number: Optional[int]
    verbatim_chunk_text: str
    confidence_score: float
    vector_score: float
    rerank_score: float


@dataclass
class FormattedCitationOutput:
    """Dataclass representing formatted citation output string and structured objects."""

    citations: List[Citation]
    formatted_citations_text: str
    overall_confidence: float


class CitationFormatter:
    """Formats exact chunk citations and multi-source confidence scores."""

    @staticmethod
    def format_citations(
        ranked_chunks: List[Any],
        snippet_max_len: int = 300,
    ) -> FormattedCitationOutput:
        """Format ranked chunks into structured Citation objects and printable string."""
        citations: List[Citation] = []
        formatted_lines: List[str] = []
        confidences: List[float] = []

        for idx, chunk in enumerate(ranked_chunks, start=1):
            if hasattr(chunk, "metadata"):
                meta = chunk.metadata
                text = getattr(chunk, "text", "") or meta.get("text", "")
                rerank_score = getattr(chunk, "rerank_score", meta.get("score", 0.0))
            else:
                meta = chunk.get("metadata", {})
                text = chunk.get("text", "")
                rerank_score = chunk.get("score", 0.0)

            source_doc = meta.get("source") or meta.get("source_doc") or meta.get("source_filename") or "Knowledge Base Document"
            relative_path = meta.get("relative_path") or meta.get("relative_file_path") or ""
            heading = meta.get("heading") or meta.get("title") or "General Overview"
            heading_level = meta.get("level") or meta.get("heading_level") or 1
            page_number = meta.get("page_number")
            vector_score = meta.get("score") or meta.get("dense_score") or rerank_score

            # Combined confidence score
            conf_score = round(float(0.4 * vector_score + 0.6 * rerank_score), 4)
            confidences.append(conf_score)

            citation = Citation(
                citation_id=idx,
                source_doc=source_doc,
                relative_path=relative_path,
                heading=heading,
                heading_level=heading_level,
                page_number=page_number,
                verbatim_chunk_text=text[:snippet_max_len].strip(),
                confidence_score=conf_score,
                vector_score=round(float(vector_score), 4),
                rerank_score=round(float(rerank_score), 4),
            )
            citations.append(citation)

            # Build readable citation line
            page_str = f" (Page {page_number})" if page_number else ""
            formatted_lines.append(
                f"[{idx}] Source: {source_doc}{page_str} | Heading: '{heading}' | Path: {relative_path}\n"
                f"    Confidence: {conf_score:.4f} (Vector: {vector_score:.4f}, Rerank: {rerank_score:.4f})\n"
                f"    Verbatim Excerpt:\n      \"{text[:snippet_max_len].strip()}...\""
            )

        overall_conf = round(float(sum(confidences) / len(confidences)), 4) if confidences else 0.0
        formatted_text = "\n\n".join(formatted_lines)

        return FormattedCitationOutput(
            citations=citations,
            formatted_citations_text=formatted_text,
            overall_confidence=overall_conf,
        )
