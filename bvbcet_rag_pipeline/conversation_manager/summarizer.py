"""Production-Grade Long Conversation Memory & Summarizer Module.

Supports long multi-turn conversations (exceeding 100+ messages),
automatically compresses older conversation turns into structured summaries
within a configurable token budget, retains key entities, topics, retrieved facts,
and user goals while filtering out greetings and small talk.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from logger.logger import get_logger

logger = get_logger("conversation_summarizer")

GREETINGS_AND_SMALLTALK_PATTERNS = [
    r"^\s*(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening|greetings)\s*[!.]*\s*$",
    r"^\s*(thanks|thank\s+you|thx|ok|okay|cool|awesome|great|got\s+it)\s*[!.]*\s*$",
    r"^\s*(bye|goodbye|see\s+you)\s*[!.]*\s*$",
]

GREETING_REGEX = re.compile("|".join(GREETINGS_AND_SMALLTALK_PATTERNS), re.IGNORECASE)


@dataclass
class SummaryResult:
    """Dataclass holding structured memory state output."""

    conversation_summary: str
    current_context: List[Dict[str, str]]
    active_entities: Dict[str, str]
    topics_discussed: List[str]
    retrieved_facts: List[str]
    user_goals: List[str]
    total_turns: int
    summarized_turns: int
    estimated_tokens: int


class ConversationSummarizer:
    """Long Conversation Memory Summarizer Engine."""

    def __init__(
        self,
        token_budget: int = 1024,
        max_unsummarized_turns: int = 6,
    ) -> None:
        self.token_budget = token_budget
        self.max_unsummarized_turns = max_unsummarized_turns

        self.turns: List[Dict[str, Any]] = []
        self.running_summary: str = ""
        self.active_entities: Dict[str, str] = {}
        self.topics_discussed: Set[str] = set()
        self.retrieved_facts: List[str] = []
        self.user_goals: List[str] = []
        self.summarized_turns_count: int = 0

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (approx. 4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @staticmethod
    def is_smalltalk(text: str) -> bool:
        """Detect if text is small talk or greeting."""
        if not text or len(text.strip()) < 3:
            return True
        return bool(GREETING_REGEX.match(text.strip()))

    def add_turn(
        self,
        question: str,
        answer: str,
        entities: Optional[Dict[str, str]] = None,
        topic: Optional[str] = None,
        facts: Optional[List[str]] = None,
    ) -> SummaryResult:
        """Add a Q&A conversation turn and trigger summarization if budget/length exceeded."""
        turn_data = {
            "turn_id": len(self.turns) + 1,
            "question": question,
            "answer": answer,
            "entities": entities or {},
            "topic": topic or "General Inquiry",
            "facts": facts or [],
            "is_smalltalk": self.is_smalltalk(question) and self.is_smalltalk(answer),
        }
        self.turns.append(turn_data)

        # Update entity and topic memory registries
        if entities:
            self.active_entities.update(entities)
        if topic:
            self.topics_discussed.add(topic)
        if facts:
            for fact in facts:
                if fact not in self.retrieved_facts:
                    self.retrieved_facts.append(fact)

        # Infer user goal if turn contains meaningful question
        if not turn_data["is_smalltalk"] and len(question.strip()) > 10:
            goal_snippet = f"User inquired about: '{question.strip()}'"
            if goal_snippet not in self.user_goals:
                self.user_goals.append(goal_snippet)

        # Check if compression/summarization is needed
        unsummarized = self.turns[self.summarized_turns_count :]
        current_token_count = sum(
            self.estimate_tokens(t["question"]) + self.estimate_tokens(t["answer"])
            for t in unsummarized
        )

        if len(unsummarized) > self.max_unsummarized_turns or current_token_count > self.token_budget:
            self._compress_older_turns()

        return self.get_summary()

    def _compress_older_turns(self) -> None:
        """Compress older turns into running summary while retaining key facts."""
        unsummarized = self.turns[self.summarized_turns_count :]
        if len(unsummarized) <= 2:
            return  # Keep at least 2 recent turns intact

        # Select turns to compress (all except last 2 turns)
        turns_to_compress = unsummarized[:-2]
        new_summary_parts: List[str] = []

        if self.running_summary:
            new_summary_parts.append(self.running_summary)

        for turn in turns_to_compress:
            if turn["is_smalltalk"]:
                continue  # Filter out greetings / small talk

            q_clean = turn["question"].strip()
            a_clean = turn["answer"].strip()
            # Truncate long answer snippets for compact summary
            a_short = a_clean[:120] + "..." if len(a_clean) > 120 else a_clean

            entry = f"- Q: {q_clean} | Key Info: {a_short}"
            if entry not in new_summary_parts:
                new_summary_parts.append(entry)

        self.running_summary = "\n".join(new_summary_parts)
        self.summarized_turns_count += len(turns_to_compress)

        logger.info(
            f"Summarized {len(turns_to_compress)} older turns. "
            f"Total summarized: {self.summarized_turns_count}/{len(self.turns)}"
        )

    def get_summary(self) -> SummaryResult:
        """Generate current structured conversation memory output."""
        recent_turns = self.turns[self.summarized_turns_count :]
        recent_context = [
            {"question": t["question"], "answer": t["answer"]}
            for t in recent_turns
        ]

        summary_tokens = self.estimate_tokens(self.running_summary)
        context_tokens = sum(
            self.estimate_tokens(t["question"]) + self.estimate_tokens(t["answer"])
            for t in recent_turns
        )
        total_tokens = summary_tokens + context_tokens

        return SummaryResult(
            conversation_summary=self.running_summary or "No older history summarized yet.",
            current_context=recent_context,
            active_entities=dict(self.active_entities),
            topics_discussed=sorted(list(self.topics_discussed)),
            retrieved_facts=list(self.retrieved_facts[-10:]),  # Keep top 10 facts
            user_goals=list(self.user_goals[-5:]),            # Keep top 5 goals
            total_turns=len(self.turns),
            summarized_turns=self.summarized_turns_count,
            estimated_tokens=total_tokens,
        )
