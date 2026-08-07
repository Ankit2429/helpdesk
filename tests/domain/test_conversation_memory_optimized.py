"""Comprehensive unit test suite for optimized ConversationMemory, SessionManager,
QueryRewriter multi-turn pronoun resolution, and token budget management.
"""

import time
import pytest
from campus_helpdesk.domain.memory.conversation_memory import ConversationMemory
from campus_helpdesk.application.session_manager import SessionManager
from campus_helpdesk.application.query_rewriter import QueryRewriter
from campus_helpdesk.config.settings import get_settings


class TestConversationMemoryUnit:
    """Unit tests for ConversationMemory core capabilities."""

    def test_multi_turn_history_storage(self):
        memory = ConversationMemory(max_history_turns=5)
        for i in range(3):
            memory.add_message("user", f"Question {i+1}")
            memory.add_message("assistant", f"Answer {i+1}")

        messages = memory.get_messages()
        assert len(messages) == 6
        assert messages[0]["content"] == "Question 1"
        assert messages[-1]["content"] == "Answer 3"

    def test_context_summarization_on_overflow(self):
        """When history exceeds max_history_turns, older messages must be condensed into summary."""
        memory = ConversationMemory(max_history_turns=2)

        # Turn 1
        memory.add_message("user", "Where is the Central Library located?")
        memory.add_message("assistant", "It is located in Block C, 2nd Floor.")

        # Turn 2
        memory.add_message("user", "What are the library opening hours?")
        memory.add_message("assistant", "The library is open from 8 AM to 8 PM.")

        # Turn 3 (Triggers overflow of Turn 1)
        memory.add_message("user", "Who is the librarian?")
        memory.add_message("assistant", "The chief librarian is Dr. Ramesh.")

        summary, recent = memory.get_history_and_summary()

        # Recent turns should contain 2 turns (4 messages)
        assert len(recent) == 4
        assert recent[0]["content"] == "What are the library opening hours?"

        # Summary should retain key facts from Turn 1
        assert summary != ""
        assert "Central Library" in summary or "Block C" in summary or "Q:" in summary

    def test_token_estimation_and_breakdown(self):
        memory = ConversationMemory(max_context_tokens=2048)
        memory.add_message("user", "Where is the library?")
        memory.add_message("assistant", "Ground floor.")

        sys_prompt = "You are a helpful campus assistant."
        context_str = "The central library is located on the ground floor of the administrative building."
        query = "What time does it close?"

        breakdown = memory.get_token_breakdown(
            system_prompt=sys_prompt,
            context_str=context_str,
            user_query=query,
        )

        assert breakdown["system_prompt_tokens"] > 0
        assert breakdown["conversation_history_tokens"] > 0
        assert breakdown["retrieved_context_tokens"] > 0
        assert breakdown["user_query_tokens"] > 0
        assert breakdown["total_tokens"] == (
            breakdown["system_prompt_tokens"] +
            breakdown["conversation_history_tokens"] +
            breakdown["retrieved_context_tokens"] +
            breakdown["user_query_tokens"]
        )
        assert breakdown["is_within_budget"] is True

    def test_token_budget_truncation(self):
        """When total tokens exceed budget, context and history are truncated safely."""
        memory = ConversationMemory(max_context_tokens=150)  # Very tight token budget
        memory.add_message("user", "Tell me everything about the university history.")
        memory.add_message("assistant", "KLE Technological University was established in 1947 as BVB College.")

        sys_prompt = "You are a helpful campus assistant."
        huge_context = "Word " * 500  # ~500 tokens
        query = "What about fees?"

        hist_str, trimmed_context, safe_query = memory.truncate_to_token_budget(
            system_prompt=sys_prompt,
            context_str=huge_context,
            user_query=query,
            max_tokens=150,
        )

        # Context must be truncated
        assert len(trimmed_context) < len(huge_context)
        assert "[context truncated" in trimmed_context or len(trimmed_context) <= 400

    def test_memory_clear(self):
        memory = ConversationMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        memory.clear()

        assert len(memory.get_messages()) == 0
        assert memory.summary == ""
        assert memory.active_topic is None


class TestMultiTurnQueryRewriting:
    """Unit tests for QueryRewriter multi-turn pronoun resolution and topic drift."""

    def test_three_turn_followup_chain(self):
        """Test chain: 'Where is the library?' -> 'What are its timings?' -> 'Is it open today?'"""
        rewriter = QueryRewriter()

        # Turn 1
        q1 = "Where is the library?"
        r1 = rewriter.rewrite(q1, history=[])
        assert "library" in r1.lower()

        # Turn 2
        history_after_turn1 = [
            {"role": "user", "content": "Where is the library?"},
            {"role": "assistant", "content": "The library is in Block C."},
        ]
        q2 = "What are its timings?"
        r2 = rewriter.rewrite(q2, history=history_after_turn1)
        assert "library" in r2.lower()

        # Turn 3
        history_after_turn2 = [
            {"role": "user", "content": "Where is the library?"},
            {"role": "assistant", "content": "The library is in Block C."},
            {"role": "user", "content": "What are its timings?"},
            {"role": "assistant", "content": "It opens at 8 AM."},
        ]
        q3 = "Is it open today?"
        r3 = rewriter.rewrite(q3, history=history_after_turn2)
        assert "library" in r3.lower()
        assert "its timings" not in r3.lower()  # Must resolve to Library, not "Its Timings"!

    def test_topic_change_prevents_stale_context_pollution(self):
        """When user switches topic from Library to Hostel, old topic must not pollute new query."""
        rewriter = QueryRewriter()
        history_library = [
            {"role": "user", "content": "Where is the library?"},
            {"role": "assistant", "content": "The library is in Block C."},
            {"role": "user", "content": "What are its timings?"},
            {"role": "assistant", "content": "It opens at 8 AM."},
        ]

        # New query changes topic to Hostel
        q_topic_shift = "Where is the boys hostel?"
        r_shift = rewriter.rewrite(q_topic_shift, history=history_library)

        assert "hostel" in r_shift.lower()
        # Should not inject 'library' into the new hostel query
        assert "library" not in r_shift.lower()

    def test_pronoun_resolution_retains_academic_acronyms(self):
        rewriter = QueryRewriter()
        q = "Tell me about CSE department"
        r = rewriter.rewrite(q, history=[])
        assert "Computer Science" in r or "CSE" in r


class TestSessionLifecycleManager:
    """Unit tests for SessionManager persistence, TTL expiration, and clear operations."""

    def test_session_creation_and_retrieval(self):
        sm = SessionManager(ttl_seconds=60, max_history_turns=5)
        m1 = sm.get_or_create_session("sess-100")
        m1.add_message("user", "Hello")

        m2 = sm.get_or_create_session("sess-100")
        assert len(m2.get_messages()) == 1

    def test_explicit_session_clear(self):
        sm = SessionManager()
        m1 = sm.get_or_create_session("sess-200")
        m1.add_message("user", "Test message")

        sm.clear_session("sess-200")
        assert "sess-200" not in sm.sessions

        # Next retrieval returns brand new memory
        m2 = sm.get_or_create_session("sess-200")
        assert len(m2.get_messages()) == 0

    def test_session_ttl_cleanup(self):
        """Sessions older than ttl_seconds must be cleaned up on trigger."""
        sm = SessionManager(ttl_seconds=0.1)  # 100ms TTL for testing
        m1 = sm.get_or_create_session("short-sess")
        m1.add_message("user", "Transient question")

        time.sleep(0.2)  # Wait for TTL expiry
        sm.cleanup_expired_sessions()

        assert "short-sess" not in sm.sessions

    def test_settings_integration(self):
        settings = get_settings()
        sm = SessionManager()
        assert sm.max_history_turns == settings.memory_max_history_turns
        assert sm.ttl_seconds == settings.memory_session_ttl_seconds
