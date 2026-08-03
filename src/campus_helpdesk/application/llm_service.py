"""Application boundary for language model generation."""

from collections.abc import Iterator
from typing import Protocol


class LLMService(Protocol):
    """Generates text responses from a language model backend."""

    def generate(self, prompt: str) -> str:
        """Generate a complete response to a prompt."""

    def generate_stream(self, prompt: str) -> Iterator[str]:
        """Yield response tokens incrementally to a prompt."""

