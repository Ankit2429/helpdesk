"""Dynamic Response Length Control & Preamble Filler Stripper.

Classifies query intent (FACTUAL_QUICK vs EXPLORATORY_DETAILED), strips conversational preamble
and filler phrases ("Great question!", "As an AI assistant...", restating questions), and enforces
strict response length limits (2–4 concise sentences by default).
"""

from dataclasses import dataclass
import enum
import re
from typing import List, Tuple

from logger.logger import get_logger

logger = get_logger("response_trimmer")

# Filler & Preamble Regex Patterns
PREAMBLE_FILLER_PATTERNS: List[re.Pattern] = [
    re.compile(r"^\s*(great|good|excellent)\s+question[!.]*\s*", re.I),
    re.compile(r"^\s*(sure|certainly|of course)[,!.]*\s*(i can help with that|here is the information)[!.]*\s*", re.I),
    re.compile(r"^\s*as an (ai|campus|helpdesk)\s+(assistant|model)[,!.]*\s*", re.I),
    re.compile(r"^\s*to answer your question( regarding| about)?[^:.]*[:.]\s*", re.I),
    re.compile(r"^\s*thank you for asking[!.]*\s*", re.I),
    re.compile(r"^\s*here is what i found[^:.]*[:.]\s*", re.I),
]


class QueryIntent(str, enum.Enum):
    """Classification of user query intent."""

    FACTUAL_QUICK = "FACTUAL_QUICK"
    EXPLORATORY_DETAILED = "EXPLORATORY_DETAILED"


@dataclass
class ResponseTrimmerOutput:
    """Dataclass holding processed response text and trimming metadata."""

    trimmed_response: str
    original_sentence_count: int
    final_sentence_count: int
    filler_stripped: bool
    query_intent: QueryIntent


class ResponseTrimmer:
    """Response Trimming & Filler Stripper Engine."""

    @staticmethod
    def classify_intent(query: str) -> QueryIntent:
        """Classify user query into FACTUAL_QUICK or EXPLORATORY_DETAILED."""
        query_lower = query.lower()

        exploratory_indicators = [
            "explain", "describe", "detail", "overview", "list all",
            "step by step", "procedure for", "tell me everything", "guidelines for",
        ]

        if any(ind in query_lower for ind in exploratory_indicators):
            return QueryIntent.EXPLORATORY_DETAILED
        return QueryIntent.FACTUAL_QUICK

    @staticmethod
    def strip_preamble(text: str) -> Tuple[str, bool]:
        """Strip preamble and conversational fluff from beginning of LLM response."""
        if not text:
            return "", False

        cleaned = text.strip()
        filler_found = False

        for pattern in PREAMBLE_FILLER_PATTERNS:
            new_cleaned = pattern.sub("", cleaned).strip()
            if new_cleaned != cleaned:
                filler_found = True
                cleaned = new_cleaned

        return cleaned, filler_found

    @classmethod
    def process_response(
        self,
        raw_response: str,
        query: str,
        max_sentences: int = 4,
    ) -> ResponseTrimmerOutput:
        """Process raw LLM response: strip filler, enforce sentence limit for factual queries."""
        cleaned, filler_stripped = self.strip_preamble(raw_response)
        intent = self.classify_intent(query)

        # Sentence tokenization heuristic
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
        orig_count = len(sentences)

        if intent == QueryIntent.FACTUAL_QUICK and len(sentences) > max_sentences:
            selected_sentences = sentences[:max_sentences]
            trimmed_text = " ".join(selected_sentences)
            logger.info(f"Trimmed factual response from {orig_count} to {len(selected_sentences)} sentences.")
        else:
            trimmed_text = cleaned

        return ResponseTrimmerOutput(
            trimmed_response=trimmed_text,
            original_sentence_count=orig_count,
            final_sentence_count=len(re.split(r"(?<=[.!?])\s+", trimmed_text)),
            filler_stripped=filler_stripped,
            query_intent=intent,
        )
