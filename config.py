"""
config.py

Central configuration settings for AUNTII Offline Helpdesk Robot.
Supports environment variables and .env configuration.
"""

import os
from pathlib import Path

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file if python-dotenv is present
try:
    from dotenv import load_dotenv
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    pass

# Ollama & LLM Settings
OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_OUTPUT_TOKENS", os.getenv("OLLAMA_MAX_TOKENS", "512")))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180.0"))

# Default System Persona
SYSTEM_PERSONA = (
    "You are AUNTII, an offline AI campus helpdesk assistant for KLE Technological University (BVB), Hubballi."
)
