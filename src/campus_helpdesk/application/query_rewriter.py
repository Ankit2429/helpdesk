"""Standalone Query Rewriter for multi-turn RAG retrieval."""

import re
from typing import Any
from collections.abc import Sequence

from campus_helpdesk.domain.conversation import ChatMessage


class QueryRewriter:
    """Rewrites follow-up questions into standalone queries based on dialogue context."""

    PRONOUN_PATTERN = re.compile(
        r"\b(it|its|they|their|them|that|this|the place|the department|there|here)\b",
        re.IGNORECASE,
    )

    def rewrite(self, query: str, history: Any) -> str:
        """Rewrite follow-up query into standalone query if it references prior topics."""
        query_text = query.strip()
        if not history:
            return query_text

        # Check if query contains follow-up pronouns or is a short fragment
        has_pronoun = bool(self.PRONOUN_PATTERN.search(query_text))
        if not has_pronoun:
            return query_text

        last_user_msg = None
        if isinstance(history, str):
            for line in reversed(history.split("\n")):
                if line.lower().startswith("user:"):
                    last_user_msg = line.split(":", 1)[1].strip()
                    break
        elif isinstance(history, (list, tuple)):
            for msg in reversed(history):
                role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
                if role == "user":
                    last_user_msg = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else str(msg))
                    break

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
