"""Exceptions raised by application services."""


class LLMServiceError(RuntimeError):
    """Raised when the configured language model cannot produce a response."""
