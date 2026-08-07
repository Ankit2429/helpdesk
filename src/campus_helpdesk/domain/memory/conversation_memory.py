import math
from threading import RLock


class ConversationMemory:
    """Thread-safe conversation memory storing message turns with automatic
    summarization of older turns, topic tracking, and token budget management.
    """

    def __init__(
        self,
        max_history_turns: int = 5,
        summary_trigger_turns: int = 5,
        max_context_tokens: int = 2048,
    ):
        self.max_history_turns = max_history_turns
        self.summary_trigger_turns = max(1, summary_trigger_turns)
        self.max_context_tokens = max_context_tokens
        self.messages: list[dict[str, str]] = []
        self.summary: str = ""
        self.active_topic: str | None = None
        self._lock = RLock()

    def add_message(self, role: str, content: str):
        """Append message to active history. When history exceeds limits, summarize
        older turns into concise summary points instead of discarding them.
        """
        with self._lock:
            self.messages.append({"role": role, "content": content})
            self._update_active_topic(content)
            self._apply_summarization_and_trimming()

    def _update_active_topic(self, content: str):
        """Extract key domain entities from message to maintain active topic state."""
        clean = content.strip().lower()
        topic_keywords = [
            ("library", "Central Library"),
            ("canteen", "Canteen & Dining"),
            ("mess", "Canteen & Dining"),
            ("hostel", "Hostel Facilities"),
            ("placement", "Placement Cell"),
            ("admission", "Admissions Office"),
            ("fee", "Fees & Accounts"),
            ("scholarship", "Scholarships"),
            ("exam", "Examinations & Timetable"),
            ("timetable", "Examinations & Timetable"),
            ("department", "Academic Departments"),
            ("computer science", "Computer Science Department"),
            ("mechanical", "Mechanical Engineering Department"),
            ("civil", "Civil Engineering Department"),
            ("biotech", "Biotechnology Department"),
            ("sports", "Sports & Gymnasium"),
        ]
        for key, domain in topic_keywords:
            if key in clean:
                self.active_topic = domain
                break

    def _apply_summarization_and_trimming(self):
        """Summarize turns exceeding max_history_turns into self.summary."""
        max_messages = self.max_history_turns * 2
        if len(self.messages) > max_messages:
            # Ensure we trim in complete (user, assistant) turn pairs
            overflow_count = len(self.messages) - max_messages
            # Round up to even number if there are enough messages
            if overflow_count % 2 != 0:
                overflow_count += 1

            if overflow_count <= len(self.messages):
                overflow_messages = self.messages[:overflow_count]
                self.messages = self.messages[overflow_count:]
                self._summarize_overflow(overflow_messages)

    def _summarize_overflow(self, overflow_messages: list[dict[str, str]]):
        """Extract concise factual points from overflowed messages into self.summary."""
        summary_parts = []
        if self.summary:
            summary_parts.append(self.summary)

        current_user_q = ""
        for msg in overflow_messages:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if role == "user":
                current_user_q = content
            elif role == "assistant" and current_user_q:
                # Condense pair into concise summary bullet
                brief_q = current_user_q[:60] + ("..." if len(current_user_q) > 60 else "")
                brief_a = content[:90] + ("..." if len(content) > 90 else "")
                summary_parts.append(f"Q: {brief_q} -> A: {brief_a}")
                current_user_q = ""

        # Limit total summary length to avoid runaway growth (keep last 5 summary points)
        if len(summary_parts) > 5:
            summary_parts = summary_parts[-5:]

        self.summary = " | ".join(summary_parts)

    def get_messages(self) -> list[dict[str, str]]:
        """Return a copy of the active message history."""
        with self._lock:
            return list(self.messages)

    def get_history_and_summary(self) -> tuple[str, list[dict[str, str]]]:
        """Return both the condensed summary of past turns and active message history."""
        with self._lock:
            return self.summary, list(self.messages)

    def get_formatted_history(self) -> str:
        """Format history for LLM prompt inclusion."""
        with self._lock:
            parts = []
            if self.summary:
                parts.append(f"Prior Conversation Summary:\n{self.summary}")
            if self.messages:
                turns_str = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in self.messages])
                parts.append(f"Recent Turns:\n{turns_str}")
            return "\n\n".join(parts)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text using standard ~3.8 chars/token ratio."""
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 3.8))

    def get_token_breakdown(
        self,
        system_prompt: str = "",
        context_str: str = "",
        user_query: str = "",
    ) -> dict[str, int]:
        """Measure token usage for system prompt, conversation history, retrieved context,
        and user query separately.
        """
        with self._lock:
            formatted_history = self.get_formatted_history()

            sys_tokens = self.estimate_tokens(system_prompt)
            hist_tokens = self.estimate_tokens(formatted_history)
            ctx_tokens = self.estimate_tokens(context_str)
            query_tokens = self.estimate_tokens(user_query)

            total = sys_tokens + hist_tokens + ctx_tokens + query_tokens
            return {
                "system_prompt_tokens": sys_tokens,
                "conversation_history_tokens": hist_tokens,
                "retrieved_context_tokens": ctx_tokens,
                "user_query_tokens": query_tokens,
                "total_tokens": total,
                "max_context_tokens": self.max_context_tokens,
                "is_within_budget": total <= self.max_context_tokens,
            }

    def truncate_to_token_budget(
        self,
        system_prompt: str,
        context_str: str,
        user_query: str,
        max_tokens: int | None = None,
    ) -> tuple[str, str, str]:
        """Ensure total token count stays strictly within max_tokens. Dynamically trims
        retrieved context or older history if limits are exceeded.
        """
        limit = max_tokens or self.max_context_tokens
        with self._lock:
            hist_str = self.get_formatted_history()
            breakdown = self.get_token_breakdown(system_prompt, context_str, user_query)

            if breakdown["total_tokens"] <= limit:
                return hist_str, context_str, user_query

            # Budget calculation
            sys_tok = breakdown["system_prompt_tokens"]
            query_tok = breakdown["user_query_tokens"]
            available = max(50, limit - sys_tok - query_tok)

            # Allocate 70% of available to RAG context, 30% to history
            context_budget_chars = int(available * 0.70 * 3.8)
            history_budget_chars = int(available * 0.30 * 3.8)

            trimmed_context = context_str
            if len(context_str) > context_budget_chars:
                trimmed_context = context_str[:context_budget_chars] + "\n...[context truncated for token budget]"

            trimmed_history = hist_str
            if len(hist_str) > history_budget_chars:
                trimmed_history = hist_str[-history_budget_chars:]

            return trimmed_history, trimmed_context, user_query

    def clear(self):
        """Reset conversation memory, summary, and topic state."""
        with self._lock:
            self.messages.clear()
            self.summary = ""
            self.active_topic = None
