"""Standalone Query Rewriter for multi-turn RAG retrieval."""

import re
from collections.abc import Sequence

from campus_helpdesk.domain.conversation import ChatMessage


class QueryRewriter:
    """Rewrites follow-up questions into standalone queries based on dialogue context."""

    PRONOUN_PATTERN = re.compile(
        r"\b(it|its|they|their|them|that|this|the place|the department|there|here)\b",
        re.IGNORECASE,
    )

    def rewrite(self, query: str, history: Sequence[ChatMessage]) -> str:
        """Rewrite follow-up query into standalone query if it references prior topics."""
        query_text = query.strip()
        if not history:
            return query_text

        # Check if query contains follow-up pronouns or is a short fragment
        has_pronoun = bool(self.PRONOUN_PATTERN.search(query_text))
        is_short_followup = len(query_text.split()) <= 4 and any(
            w in query_text.lower()
            for w in ("timing", "timings", "hour", "hours", "where", "who", "fee", "fees", "contact", "email", "phone")
        )

        if not (has_pronoun or is_short_followup):
            return query_text

        # Extract last user query subject or main entity
        last_user_msg = next((msg.content for msg in reversed(history) if msg.role == "user"), None)
        if not last_user_msg:
            return query_text

        subject = self._extract_subject(last_user_msg)
        if not subject:
            return query_text

        if has_pronoun:
            standalone = self.PRONOUN_PATTERN.sub(subject, query_text)
            return standalone
        else:
            return f"{query_text} of {subject}"

    def _extract_subject(self, text: str) -> str | None:
        """Extract primary subject noun phrase from previous user question."""
        clean = text.strip().rstrip("?").rstrip(".")
        lower_clean = clean.lower()

        prefixes = [
            "where is the",
            "where is",
            "what is the",
            "what is",
            "when is the",
            "when is",
            "tell me about the",
            "tell me about",
            "how to apply for",
            "how to get into",
        ]
        for prefix in prefixes:
            if lower_clean.startswith(prefix):
                sub = clean[len(prefix) :].strip()
                if sub:
                    # Strip trailing location verbs
                    for suffix in [" located in campus", " located", " situated", " on campus"]:
                        if sub.lower().endswith(suffix):
                            sub = sub[: -len(suffix)].strip()
                    return sub.title()

        return clean.title()
