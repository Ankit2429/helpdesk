"""Unit tests for TopicTracker and EntityResolver modules."""

from conversation_manager.entity_resolver import EntityResolver, EntityResult
from conversation_manager.summarizer import ConversationSummarizer, SummaryResult
from conversation_manager.topic_tracker import TopicResult, TopicTracker


def test_topic_tracker_detection():
    tracker = TopicTracker(model_name="all-MiniLM-L6-v2")

    # Test Department Detection
    res1 = tracker.process_turn("What courses are offered in Computer Science?")
    assert res1.active_topic == "Departments" or res1.active_topic == "Courses"
    assert res1.topic_confidence > 0.0

    # Test Hostels Detection
    res2 = tracker.process_turn("Tell me about the boys hostel fee structure.")
    assert res2.active_topic in ["Hostels", "Admissions"]
    assert res2.topic_confidence > 0.0

    # Test Topic Continuation
    res3 = tracker.process_turn("What are the hostel mess timings?", previous_query="Tell me about the boys hostel fee structure.")
    assert res3.action == "Continue topic"


def test_entity_resolver():
    resolver = EntityResolver()

    # Pre-populate context with previous turn mentioning Computer Science and B-Block
    context = [
        {
            "question": "Where is Computer Science department located?",
            "answer": "Computer Science department is located in B-Block.",
        }
    ]

    # Test pronoun resolution
    res = resolver.resolve("What courses does it offer?", conversation_context=context)

    assert isinstance(res, EntityResult)
    assert "Computer Science" in res.resolved_query or "B-Block" in res.resolved_query
    assert res.entity_confidence > 0.0


def test_conversation_summarizer():
    summarizer = ConversationSummarizer(max_unsummarized_turns=3)

    # Add 5 turns (exceeds max_unsummarized_turns=3)
    summarizer.add_turn("hi", "Hello! How can I help you?", topic="Greetings")
    summarizer.add_turn("Where is Computer Science located?", "Computer Science is in B-Block.", entities={"department": "Computer Science", "building": "B-Block"}, topic="Departments")
    summarizer.add_turn("What is the eligibility for B.E. admissions?", "KCET rank under 15000.", topic="Admissions")
    summarizer.add_turn("What are the hostel fees?", "Hostel fees are 60,000 INR per year.", topic="Hostels")
    summary_res = summarizer.add_turn("Who is the head of Computer Science?", "Dr. Ashok Shettar is the department head.", topic="Faculty")

    assert isinstance(summary_res, SummaryResult)
    assert summary_res.total_turns == 5
    assert summary_res.summarized_turns > 0
    assert "Computer Science" in summary_res.active_entities.values() or "B-Block" in summary_res.active_entities.values()
    assert len(summary_res.current_context) <= 3
