"""Query Rewriter Engine.

Converts ambiguous follow-up questions into standalone explicit queries using
conversation memory context.
"""

import re
from typing import List, Optional, Protocol
from conversation.memory import ChatMessage
from logger.logger import get_logger

logger = get_logger("query_rewriter")


class QueryRewriterEngine(Protocol):
    """Protocol interface for Query Rewriter backends."""

    def rewrite(self, current_query: str, history: List[ChatMessage]) -> str:
        """Rewrite current query using history context."""
        ...


class RuleBasedQueryRewriter:
    """Rule-based and pronoun resolution query rewriter engine."""

    PRONOUNS = ["he", "she", "it", "they", "this", "that", "those", "there", "its", "their", "his", "her"]

    SHORT_FOLLOWUP_TRIGGERS = [
        "fee", "fees", "cost", "eligibility", "cutoff", "duration",
        "placements", "salary", "hod", "head", "location", "building",
        "founder", "founded", "who", "when", "where",
    ]

    def rewrite(self, current_query: str, history: List[ChatMessage]) -> str:
        """Convert follow-up query into standalone query using prior turns."""
        if not current_query or not current_query.strip():
            return current_query

        clean_q = current_query.strip()
        words = clean_q.lower().split()

        if not history:
            return clean_q

        # Find previous user & assistant context entities
        last_user_turn = None
        last_assistant_turn = None

        for msg in reversed(history):
            if msg.role == "user" and not last_user_turn:
                last_user_turn = msg.content
            elif msg.role == "assistant" and not last_assistant_turn:
                last_assistant_turn = msg.content
            if last_user_turn and last_assistant_turn:
                break

        if not last_user_turn:
            return clean_q

        topic_subject = self._extract_subject(last_user_turn)
        if not topic_subject:
            return clean_q

        # Case 1: Direct pronoun replacement (e.g. "Who founded it?", "Where is it?")
        rewritten = clean_q
        pronoun_found = False
        for p in self.PRONOUNS:
            pattern = r"\b" + p + r"\b"
            if re.search(pattern, rewritten, flags=re.I):
                rewritten = re.sub(pattern, topic_subject, rewritten, flags=re.I)
                pronoun_found = True

        if pronoun_found:
            logger.info(f"Query Rewritten (Pronoun): '{current_query}' -> '{rewritten}'")
            return rewritten

        # Case 2: Short follow-up query (e.g. "Fees?", "Eligibility?", "Who founded?")
        if len(words) <= 4 and any(trig in clean_q.lower() for trig in self.SHORT_FOLLOWUP_TRIGGERS):
            if "fee" in clean_q.lower() or "cost" in clean_q.lower():
                rewritten = f"What are the fees for {topic_subject}?"
            elif "eligibility" in clean_q.lower():
                rewritten = f"What is the eligibility criteria for {topic_subject}?"
            elif "cutoff" in clean_q.lower():
                rewritten = f"What is the cutoff for {topic_subject}?"
            elif "placement" in clean_q.lower() or "salary" in clean_q.lower():
                rewritten = f"What are the placement statistics for {topic_subject}?"
            elif "founder" in clean_q.lower() or "founded" in clean_q.lower() or "who" in clean_q.lower():
                rewritten = f"Who founded {topic_subject}?"
            else:
                rewritten = f"What about {clean_q} regarding {topic_subject}?"

            logger.info(f"Query Rewritten (Follow-up): '{current_query}' -> '{rewritten}'")
            return rewritten

        return clean_q

    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract primary entity subject from text."""
        clean = text.strip()
        prefixes = [
            "what is", "tell me about", "details of", "information on",
            "when do", "where is", "who is", "how to", "about",
        ]
        lower_clean = clean.lower()
        for p in prefixes:
            if lower_clean.startswith(p):
                clean = clean[len(p):].strip("? ")
                break
        return clean.strip("? ") if clean else None


class QueryRewriter:
    """Facade for Query Rewriter engine with injectable backend."""

    def __init__(self, engine: Optional[QueryRewriterEngine] = None) -> None:
        self.engine = engine or RuleBasedQueryRewriter()

    def rewrite(self, current_query: str, history: List[ChatMessage]) -> str:
        """Rewrite current user query into standalone query."""
        return self.engine.rewrite(current_query, history)
