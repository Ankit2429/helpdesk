"""Conversation-Aware Query Contextualizer & Session Cache Engine.

Rewrites follow-up queries using prior conversation turns (query expansion/contextualization),
determines whether follow-ups require new vector retrieval vs existing context cache,
and maintains a rolling retrieval cache per session.
"""

from dataclasses import dataclass, field
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from conversation_manager.entity_resolver import EntityResolver
from logger.logger import get_logger

logger = get_logger("query_contextualizer")

FOLLOWUP_PRONOUN_PATTERN = re.compile(
    r"\b(it|he|she|his|her|their|there|that|this|those|previous department|previous building|previous faculty)\b",
    re.IGNORECASE,
)


@dataclass
class ContextualizedQueryOutput:
    """Dataclass holding contextualized query result."""

    original_query: str
    contextualized_query: str
    needs_new_retrieval: bool
    cached_chunks: List[Any] = field(default_factory=list)
    resolved_references: Dict[str, str] = field(default_factory=dict)


class QueryContextualizer:
    """Session Retrieval Cache & Query Contextualizer Engine."""

    def __init__(self, cache_ttl_turns: int = 5) -> None:
        self.cache_ttl_turns = cache_ttl_turns
        self.entity_resolver = EntityResolver()
        self.session_retrieval_cache: Dict[str, List[Any]] = {}
        self.turn_retrieval_history: List[Tuple[str, List[Any]]] = []

    def clear_session_cache(self) -> None:
        """Clear session retrieval cache."""
        self.session_retrieval_cache = {}
        self.turn_retrieval_history = []
        logger.info("Session retrieval cache cleared.")

    @staticmethod
    def get_query_hash(query: str) -> str:
        """Calculate query string hash for cache lookups."""
        return hashlib.sha256(query.lower().strip().encode("utf-8")).hexdigest()

    def contextualize_query(
        self,
        query: str,
        conversation_context: List[Dict[str, str]],
    ) -> ContextualizedQueryOutput:
        """Rewrite user query using prior conversation history and check session retrieval cache."""
        # Step 1: Resolve coreferences and entities using EntityResolver
        entity_res = self.entity_resolver.resolve(query, conversation_context=conversation_context)
        contextualized_query = entity_res.resolved_query

        # If query is short or implicit follow-up without coreference, append recent topic context
        if conversation_context and len(query.split()) <= 4 and not entity_res.resolved_references:
            last_turn = conversation_context[-1]
            last_q = last_turn.get("question", "")
            if last_q:
                contextualized_query = f"{contextualized_query} (In context of: {last_q})"

        query_hash = self.get_query_hash(contextualized_query)

        # Step 2: Check Session Retrieval Cache
        if query_hash in self.session_retrieval_cache:
            logger.info(f"Query Contextualizer: Cache HIT for '{contextualized_query}'")
            return ContextualizedQueryOutput(
                original_query=query,
                contextualized_query=contextualized_query,
                needs_new_retrieval=False,
                cached_chunks=self.session_retrieval_cache[query_hash],
                resolved_references=entity_res.resolved_references,
            )

        # Check if question is pure greeting/gratitude that doesn't need retrieval
        is_greeting = bool(re.match(r"^\s*(hi|hello|thanks|thank\s+you|ok|bye)\s*[!.]*\s*$", query, re.I))
        if is_greeting:
            return ContextualizedQueryOutput(
                original_query=query,
                contextualized_query=contextualized_query,
                needs_new_retrieval=False,
                cached_chunks=[],
                resolved_references=entity_res.resolved_references,
            )

        logger.info(f"Query Contextualizer: Cache MISS. Original='{query}' -> Contextualized='{contextualized_query}'")
        return ContextualizedQueryOutput(
            original_query=query,
            contextualized_query=contextualized_query,
            needs_new_retrieval=True,
            cached_chunks=[],
            resolved_references=entity_res.resolved_references,
        )

    def cache_retrieval_result(self, contextualized_query: str, chunks: List[Any]) -> None:
        """Store retrieval results in rolling session cache."""
        query_hash = self.get_query_hash(contextualized_query)
        self.session_retrieval_cache[query_hash] = chunks
        self.turn_retrieval_history.append((contextualized_query, chunks))

        # Evict oldest entries if cache exceeds TTL turns
        if len(self.turn_retrieval_history) > self.cache_ttl_turns:
            oldest_q, _ = self.turn_retrieval_history.pop(0)
            oldest_hash = self.get_query_hash(oldest_q)
            self.session_retrieval_cache.pop(oldest_hash, None)
