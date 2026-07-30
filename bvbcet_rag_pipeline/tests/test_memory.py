"""Unit tests for ConversationMemory."""

from conversation.memory import ConversationMemory


def test_conversation_memory_append_and_retrieve():
    mem = ConversationMemory(max_history_size=10)
    assert len(mem.get_history()) == 0

    mem.add_user_message("What is KLE Tech?")
    mem.add_assistant_message("KLE Tech is a university in Hubballi.")

    history = mem.get_history()
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "What is KLE Tech?"
    assert history[1].role == "assistant"


def test_conversation_memory_sliding_window():
    mem = ConversationMemory(max_history_size=4)
    for i in range(6):
        mem.add_user_message(f"Msg {i}")

    history = mem.get_history()
    assert len(history) == 4
    assert history[0].content == "Msg 2"
    assert history[-1].content == "Msg 5"


def test_conversation_memory_clear_and_export():
    mem = ConversationMemory()
    mem.add_user_message("Hello")
    exported = mem.export_history()
    assert len(exported) == 1
    assert exported[0]["content"] == "Hello"

    mem.clear()
    assert len(mem.get_history()) == 0
