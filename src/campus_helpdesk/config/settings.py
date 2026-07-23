"""Typed environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional `.env` file."""

    app_env: str = "development"
    app_name: str = "Campus Helpdesk"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str
    ollama_timeout_seconds: float = 180.0
    ollama_temperature: float = 0.2
    ollama_top_p: float = 0.8
    ollama_top_k: int = 40
    ollama_repeat_penalty: float = 1.1
    ollama_context_window: int = 8_192
    ollama_max_output_tokens: int = 512
    knowledge_source_path: Path = Path("data/knowledge")
    knowledge_max_file_size_bytes: int = 20_000_000
    faiss_index_path: Path = Path("data/faiss")
    faiss_allow_dangerous_deserialization: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_normalize: bool = True
    embedding_show_progress: bool = False
    embedding_local_files_only: bool = False
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_chunk_separators: list[str] = Field(default_factory=lambda: ["\n\n", "\n", " ", ""])
    rag_add_start_index: bool = True
    rag_search_limit: int = 4
    rag_distance_threshold: float = 1.0
    webcam_index: int = 0
    camera_fps: int = 15
    person_detection_reset_frames: int = 30
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    tts_voice_model: str = "en_US-lessac-medium"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator(
        "embedding_batch_size",
        "knowledge_max_file_size_bytes",
        "rag_chunk_size",
        "rag_search_limit",
    )
    @classmethod
    def require_positive_values(cls, value: int) -> int:
        """Reject non-positive processing and retrieval sizes."""
        if value < 1:
            raise ValueError("Value must be at least one.")
        return value

    @field_validator("rag_chunk_overlap")
    @classmethod
    def require_non_negative_overlap(cls, value: int) -> int:
        """Reject a negative chunk overlap."""
        if value < 0:
            raise ValueError("Chunk overlap cannot be negative.")
        return value

    @field_validator("ollama_timeout_seconds")
    @classmethod
    def require_positive_ollama_timeout(cls, value: float) -> float:
        """Reject a timeout that would make local model requests invalid."""
        if value <= 0:
            raise ValueError("Ollama timeout must be greater than zero.")
        return value

    @field_validator("ollama_model")
    @classmethod
    def require_ollama_model(cls, value: str) -> str:
        """Require an explicitly configured local model rather than a source-code default."""
        if not value.strip():
            raise ValueError("OLLAMA_MODEL must not be blank.")
        return value

    @field_validator("ollama_temperature")
    @classmethod
    def require_non_negative_temperature(cls, value: float) -> float:
        """Reject invalid sampling temperatures."""
        if value < 0:
            raise ValueError("Ollama temperature cannot be negative.")
        return value

    @field_validator("ollama_top_p")
    @classmethod
    def require_probability_top_p(cls, value: float) -> float:
        """Require nucleus sampling probability to be within its valid range."""
        if not 0 < value <= 1:
            raise ValueError("Ollama top-p must be greater than zero and at most one.")
        return value

    @field_validator("ollama_top_k", "ollama_context_window", "ollama_max_output_tokens")
    @classmethod
    def require_positive_ollama_integers(cls, value: int) -> int:
        """Reject non-positive local inference limits."""
        if value < 1:
            raise ValueError("Ollama inference limits must be at least one.")
        return value

    @field_validator("ollama_repeat_penalty")
    @classmethod
    def require_positive_repeat_penalty(cls, value: float) -> float:
        """Reject an invalid repetition penalty."""
        if value <= 0:
            raise ValueError("Ollama repeat penalty must be greater than zero.")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def require_loopback_ollama(cls, value: str) -> str:
        """Prevent an environment override from routing prompts to a remote host."""
        parsed_url = urlparse(value)
        if parsed_url.scheme not in {"http", "https"} or parsed_url.hostname not in {
            "127.0.0.1",
            "::1",
            "localhost",
        }:
            raise ValueError("OLLAMA_BASE_URL must use a loopback host for offline operation.")
        return value.rstrip("/")

    @field_validator("rag_chunk_separators")
    @classmethod
    def require_chunk_separators(cls, value: list[str]) -> list[str]:
        """Reject an empty separator configuration."""
        if not value:
            raise ValueError("At least one RAG chunk separator is required.")
        return value

    @model_validator(mode="after")
    def validate_chunk_settings(self) -> "Settings":
        """Ensure overlap leaves room for unique content in each chunk."""
        if self.rag_chunk_overlap >= self.rag_chunk_size:
            raise ValueError("RAG chunk overlap must be smaller than RAG chunk size.")
        return self

    @property
    def ollama_options(self) -> dict[str, float | int]:
        """Return generation options accepted by Ollama's local chat API."""
        return {
            "temperature": self.ollama_temperature,
            "top_p": self.ollama_top_p,
            "top_k": self.ollama_top_k,
            "repeat_penalty": self.ollama_repeat_penalty,
            "num_ctx": self.ollama_context_window,
            "num_predict": self.ollama_max_output_tokens,
        }


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance with friendly startup validation."""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        try:
            env_file.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass

    try:
        return Settings()
    except Exception as exc:
        missing_vars: list[str] = []
        if hasattr(exc, "errors"):
            for err in exc.errors():
                loc = err.get("loc", ())
                if loc:
                    var_name = str(loc[-1]).upper()
                    missing_vars.append(var_name)

        var_list = "\n".join(f"  - {v}" for v in missing_vars) if missing_vars else "  - OLLAMA_MODEL"

        msg = (
            "-------------------------------------\n"
            "Configuration Error\n\n"
            "Missing or invalid required configuration:\n\n"
            f"{var_list}\n\n"
            "Please create or check your .env file created from .env.example\n"
            "and set the required values.\n\n"
            "Example:\n\n"
            "OLLAMA_MODEL=qwen2.5:7b\n"
            "OLLAMA_BASE_URL=http://localhost:11434\n"
            "-------------------------------------"
        )
        raise SystemExit(msg) from None

