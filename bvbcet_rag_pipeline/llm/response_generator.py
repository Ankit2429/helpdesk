"""Modular Response Generator Engine.

Post-processes raw LLM output, applies preamble filler stripping, verifies grounding,
formats citations, and packages the result into a `FinalResponse` dataclass.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional
from langchain_core.documents import Document

from conversation.intent_classifier import Intent
from conversation_manager.hallucination_verifier import HallucinationVerifier
from conversation_manager.response_trimmer import ResponseTrimmer
from retrieval.citation_formatter import CitationFormatter
from logger.logger import get_logger

logger = get_logger("response_generator")


@dataclass
class FinalResponse:
    """Dataclass encapsulating final processed user response."""

    answer: str
    intent: Intent
    resolved_query: str
    citations: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    status: str = "success"             # 'success', 'llm_error', 'zero_retrieval', 'direct_canned_response'
    error_detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert FinalResponse to dictionary."""
        return {
            "answer": self.answer,
            "intent": self.intent.value if isinstance(self.intent, Intent) else str(self.intent),
            "resolved_query": self.resolved_query,
            "citations": self.citations,
            "sources": self.citations,
            "metrics": self.metrics,
            "status": self.status,
            "error_detail": self.error_detail,
        }


class ResponseGenerator:
    """Post-processes raw LLM responses into structured FinalResponse objects."""

    def __init__(
        self,
        citation_formatter: Optional[CitationFormatter] = None,
        hallucination_verifier: Optional[HallucinationVerifier] = None,
    ) -> None:
        self.citation_formatter = citation_formatter or CitationFormatter()
        self.hallucination_verifier = hallucination_verifier or HallucinationVerifier(grounding_threshold=0.30)

    def generate_response(
        self,
        raw_llm_answer: Optional[str],
        intent: Intent,
        resolved_query: str,
        retrieved_docs: List[Document],
        inference_time_s: float = 0.0,
        error_detail: Optional[str] = None,
    ) -> FinalResponse:
        """Process raw LLM output and return FinalResponse."""
        # Case 1: LLM Error
        if error_detail or raw_llm_answer is None:
            formatted_citations = self._build_citations(retrieved_docs)
            err_answer = (
                f"Retrieved relevant context ({len(retrieved_docs)} chunks), but the language model failed to generate a response.\n"
                f"Ollama Error Details: {error_detail}\n"
                f"Please verify Ollama service is running (`ollama serve`)."
            )
            return FinalResponse(
                answer=err_answer,
                intent=intent,
                resolved_query=resolved_query,
                citations=formatted_citations,
                metrics={"inference_time_s": inference_time_s},
                status="llm_error",
                error_detail=error_detail,
            )

        # Case 2: Zero Retrieval
        if not retrieved_docs:
            return FinalResponse(
                answer="I couldn't find that information in the college knowledge base.",
                intent=intent,
                resolved_query=resolved_query,
                citations=[],
                metrics={"inference_time_s": inference_time_s},
                status="zero_retrieval",
                error_detail=None,
            )

        # Case 3: Success — Strip Preamble Fillers & Verify Grounding
        trimmed_out = ResponseTrimmer.process_response(raw_llm_answer, resolved_query, max_sentences=4)
        verify_res = self.hallucination_verifier.verify_response(
            question=resolved_query,
            generated_answer=trimmed_out.trimmed_response,
            retrieved_chunks=retrieved_docs,
        )

        final_text = verify_res.sanitized_response
        formatted_citations = self._build_citations(retrieved_docs)

        top_confidence = max([doc.metadata.get("score", 0.0) for doc in retrieved_docs], default=0.0) if hasattr(retrieved_docs[0], "metadata") else 0.0 if retrieved_docs else 0.0

        metrics = {
            "confidence": top_confidence,
            "inference_time_s": inference_time_s,
            "grounding_score": verify_res.grounding_score,
            "is_grounded": verify_res.is_grounded,
            "filler_stripped": trimmed_out.filler_stripped,
            "chunk_count": len(retrieved_docs),
        }

        status = "success" if verify_res.is_grounded else "hallucination_flagged"

        return FinalResponse(
            answer=final_text,
            intent=intent,
            resolved_query=resolved_query,
            citations=formatted_citations,
            metrics=metrics,
            status=status,
            error_detail=None,
        )

    def _build_citations(self, retrieved_docs: List[Document]) -> List[Dict[str, Any]]:
        """Format retrieved documents into structured citation dictionaries."""
        formatted_citations = []
        for idx, doc in enumerate(retrieved_docs, start=1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            formatted_citations.append(
                {
                    "citation_number": idx,
                    "chunk_id": meta.get("chunk_id") or meta.get("id", ""),
                    "source": meta.get("source") or meta.get("source_doc", ""),
                    "heading": meta.get("heading") or "Overview",
                    "relative_path": meta.get("relative_path", ""),
                    "score": meta.get("score", 0.0),
                    "snippet": (doc.page_content[:200] + "...") if hasattr(doc, "page_content") else str(doc)[:200],
                }
            )
        return formatted_citations
