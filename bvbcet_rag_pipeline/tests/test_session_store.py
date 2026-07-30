"""Unit tests for Persistent Session Memory Store."""

from pathlib import Path
import shutil
import tempfile

from conversation_manager.session_store import SessionMemoryStore


def test_session_store_persistence():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        session_id = "test_user_session_123"
        store1 = SessionMemoryStore(session_id=session_id, sessions_dir=temp_dir)

        store1.add_turn(
            question="Where is Computer Science department?",
            answer="B-Block",
            entities={"department": "Computer Science"},
            topic="Departments",
        )

        assert len(store1.state.turn_history) == 1
        assert store1.state.active_entities.get("department") == "Computer Science"

        # Initialize new store instance loading same session file
        store2 = SessionMemoryStore(session_id=session_id, sessions_dir=temp_dir)

        assert len(store2.state.turn_history) == 1
        assert store2.state.active_entities.get("department") == "Computer Science"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
