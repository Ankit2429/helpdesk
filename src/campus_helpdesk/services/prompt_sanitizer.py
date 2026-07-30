"""Prompt sanitizer – strips known prompt-injection patterns from user input.

This module is intentionally lightweight.  Its only job is to protect the
system prompt from common injection attempts before the query reaches the LLM.
No ML or external dependencies are required.
"""

from __future__ import annotations

import re

# Patterns that indicate a deliberate attempt to override system instructions.
# We collapse them to a neutral string rather than raising an exception, so
# the user receives a graceful response instead of a crash.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
]

# Maximum input length accepted (characters).  Longer inputs are truncated.
_MAX_INPUT_LENGTH = 2_000


def sanitize_user_input(text: str) -> str:
    """Return a sanitized copy of *text* safe to pass to the LLM pipeline.

    Steps applied:
    1. Strip leading/trailing whitespace.
    2. Truncate to ``_MAX_INPUT_LENGTH`` characters.
    3. Remove control characters (except newlines and tabs).
    4. Collapse known prompt-injection patterns.
    """
    if not isinstance(text, str):
        return ""

    # Truncate
    text = text.strip()[:_MAX_INPUT_LENGTH]

    # Remove control characters (keep printable ASCII + common whitespace)
    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse injection attempts
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[redacted]", text)

    return text.strip()
