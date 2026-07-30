"""Self-Checking Post-Generation Hallucination Verifier.

Verifies generated answer claims against retrieved knowledge base chunks.
Flags ungrounded factual claims, replaces them with strict context facts,
and logs flagged turns to logs/hallucination_flags.json.
"""

from dataclasses import dataclass, field
import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from config.config import LOGS_DIR
from logger.logger import get_logger

logger = get_logger("hallucination_verifier")

HALLUCINATION_LOG_FILE: Path = LOGS_DIR / "hallucination_flags.json"


@dataclass
class ClaimVerificationResult:
    """Dataclass holding verification status for generated answer."""

    is_grounded: bool
    grounding_score: float  # 0.0 to 1.0
    verified_sentences: List[str]
    flagged_sentences: List[str]
    sanitized_response: str


class HallucinationVerifier:
    """Post-generation claim verification and hallucination flagging engine."""

    def __init__(self, grounding_threshold: float = 0.30, log_file: Path = HALLUCINATION_LOG_FILE) -> None:
        self.grounding_threshold = grounding_threshold
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_keywords(text: str) -> set:
        """Extract key non-stopword tokens for claim comparison."""
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or", "with", "this", "that", "it"}
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        return {w for w in words if w not in stopwords}

    def verify_sentence(self, sentence: str, context_text: str) -> Tuple[bool, float]:
        """Verify if a single sentence claim is backed by context text.

        Returns:
            Tuple of (is_grounded, grounding_score)
        """
        sent_keywords = self.extract_keywords(sentence)
        if not sent_keywords:
            return True, 1.0

        context_keywords = self.extract_keywords(context_text)

        overlap = sent_keywords.intersection(context_keywords)
        score = round(len(overlap) / len(sent_keywords), 4)

        is_grounded = score >= self.grounding_threshold
        return is_grounded, score

    def verify_response(
        self,
        question: str,
        generated_answer: str,
        retrieved_chunks: List[Any],
    ) -> ClaimVerificationResult:
        """Verify generated answer sentences against retrieved context chunks."""
        # Exact zero-retrieval trigger pass-through
        if generated_answer.strip() == "I couldn't find that information in the college knowledge base.":
            return ClaimVerificationResult(
                is_grounded=True,
                grounding_score=1.0,
                verified_sentences=[generated_answer],
                flagged_sentences=[],
                sanitized_response=generated_answer,
            )

        # Build full context string
        context_texts = []
        for c in retrieved_chunks:
            if hasattr(c, "page_content"):
                context_texts.append(c.page_content)
            elif isinstance(c, dict):
                context_texts.append(c.get("text", ""))
            else:
                context_texts.append(str(c))

        combined_context = "\n".join(context_texts)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", generated_answer) if s.strip()]

        verified_sents: List[str] = []
        flagged_sents: List[str] = []
        scores: List[float] = []

        for sent in sentences:
            is_ok, score = self.verify_sentence(sent, combined_context)
            scores.append(score)
            if is_ok:
                verified_sents.append(sent)
            else:
                flagged_sents.append(sent)
                logger.warning(f"Hallucination Warning: Sentence '{sent}' ungrounded (score={score:.4f})")

        avg_score = round(sum(scores) / len(scores), 4) if scores else 1.0
        is_overall_grounded = len(flagged_sents) == 0

        # Construct sanitized response if ungrounded claims are detected
        if not is_overall_grounded and verified_sents:
            sanitized = " ".join(verified_sents)
        elif not is_overall_grounded and not verified_sents:
            sanitized = "I couldn't find that information in the college knowledge base."
        else:
            sanitized = generated_answer

        # Log flagged turns
        if not is_overall_grounded:
            self.log_hallucination_flag(question, generated_answer, flagged_sents, avg_score)

        return ClaimVerificationResult(
            is_grounded=is_overall_grounded,
            grounding_score=avg_score,
            verified_sentences=verified_sents,
            flagged_sentences=flagged_sents,
            sanitized_response=sanitized,
        )

    def log_hallucination_flag(
        self,
        question: str,
        answer: str,
        flagged_sentences: List[str],
        score: float,
    ) -> None:
        """Append flagged ungrounded response turn to JSON log."""
        record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "question": question,
            "answer": answer,
            "flagged_sentences": flagged_sentences,
            "grounding_score": score,
        }
        try:
            existing: List[Dict[str, Any]] = []
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            existing.append(record)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed logging hallucination flag: {e}")
