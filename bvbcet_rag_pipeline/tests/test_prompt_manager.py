"""Unit tests for System Prompt Manager."""

from conversation_manager.prompt_manager import SystemPromptManager, V2_GROUNDED_CONCISE_PROMPT


def test_system_prompt_manager_versioning():
    manager = SystemPromptManager()

    v1 = manager.get_prompt("v1_baseline")
    assert v1.version_id == "v1_baseline"

    v2 = manager.get_prompt("v2_grounded_concise")
    assert v2.version_id == "v2_grounded_concise"

    formatted = manager.format_prompt(
        question="What courses are offered in CS?",
        context_str="B.E. Computer Science offered.",
        version_id="v2_grounded_concise",
    )

    assert "Direct, polite, factual, concise" in formatted
    assert "What courses are offered in CS?" in formatted
