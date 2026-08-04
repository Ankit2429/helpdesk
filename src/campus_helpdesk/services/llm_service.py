"""
src/campus_helpdesk/services/llm_service.py

Adapter re-exporting concrete LLMService for campus_helpdesk package architecture.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path so services.llm_service can be resolved
root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from services.llm_service import LLMService
except ImportError:
    # Fallback to local Protocol if services is unavailable
    from campus_helpdesk.application.llm_service import LLMService

__all__ = ["LLMService"]
