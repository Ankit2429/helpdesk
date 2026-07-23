"""Application boundary for language model generation."""

from typing import Protocol


class LLMService(Protocol):
    """Generates text responses from a local language model."""

    def generate(self, prompt: str) -> str:
        """Generate a response to a user prompt."""
