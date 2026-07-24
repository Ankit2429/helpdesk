"""
Response Parser

Responsible for cleaning and validating LLM responses before they are
returned to the user or sent to the TTS engine.
"""

import re
from typing import Optional


class ResponseParser:
    """
    Cleans and validates LLM responses.
    """

    def __init__(self):
        self.default_response = (
            "I'm sorry, I couldn't find the required information."
        )

    def parse(self, response: Optional[str]) -> str:
        """
        Main parser entry point.
        """

        if not response:
            return self.default_response

        response = self._remove_extra_whitespace(response)
        response = self._remove_markdown(response)
        response = self._remove_thinking_tokens(response)
        response = self._trim(response)

        if not response:
            return self.default_response

        return response

    def _remove_extra_whitespace(self, text: str) -> str:
        """
        Removes repeated spaces and blank lines.
        """
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _remove_markdown(self, text: str) -> str:
        """
        Removes simple markdown formatting.
        """

        markdown_patterns = [
            r"\*\*(.*?)\*\*",
            r"\*(.*?)\*",
            r"`(.*?)`",
            r"#+ ",
        ]

        for pattern in markdown_patterns:
            text = re.sub(pattern, r"\1", text)

        return text

    def _remove_thinking_tokens(self, text: str) -> str:
        """
        Removes internal reasoning tags if a model outputs them.
        """

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"</?think>", "", text)

        return text

    def _trim(self, text: str) -> str:
        """
        Final cleanup.
        """

        return text.strip()
        