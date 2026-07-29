"""Exceptions raised by application services.

The hierarchy is designed to enable granular handling of recoverable (transient),
non‑recoverable (fatal) and domain‑specific errors.
"""

class HelpdeskError(RuntimeError):
    """Base class for all custom errors in the campus_helpdesk application."""
    pass

class TransientError(HelpdeskError):
    """Indicates a recoverable, temporary failure (e.g., network glitch)."""
    pass

class FatalError(HelpdeskError):
    """Indicates a non‑recoverable error (e.g., misconfiguration)."""
    pass

# Domain‑specific exceptions -------------------------------------------------

class LLMServiceError(TransientError):
    """Raised when the configured language model cannot produce a response."""
    pass

class CameraError(TransientError):
    """Raised for camera hardware or capture failures."""
    pass

class AudioError(TransientError):
    """Raised for microphone / audio capture failures."""
    pass

class RetrievalError(TransientError):
    """Raised for vector‑store or retrieval‑related failures."""
    pass

class ConfigurationError(FatalError):
    """Raised when configuration validation fails or contains invalid values."""
    pass

__all__ = [
    "HelpdeskError",
    "TransientError",
    "FatalError",
    "LLMServiceError",
    "CameraError",
    "AudioError",
    "RetrievalError",
    "ConfigurationError",
]
