"""Application-level chat data structures."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatResult:
    """A response produced by the chat application service."""

    reply: str
    status: str
