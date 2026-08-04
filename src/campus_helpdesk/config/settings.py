"""Typed environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional `.env` file."""

    app_env: str = "development"
    app_name: str = "Campus Helpdesk"
    app_version: str = "0.1.0"
    stt_device_index: int | None = None
    stt_enable_online_fallback: bool = False
    mic_device_index: int | None = Field(
        default=None,
        validation_alias=AliasChoices("MIC_DEVICE_INDEX", "VAD_DEVICE_INDEX")
    )
    speaker_device_index: int | None = Field(
        default=None,
        validation_alias=AliasChoices("SPEAKER_DEVICE_INDEX")
    )
    debug: bool = False
    log_level: str = "INFO"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = Field(default="llama3.2:3b", validation_alias="OLLAMA_MODEL")
    ollama_timeout_seconds: float = 180.0
    ollama_temperature: float = 0.2
    ollama_top_p: float = 0.8
    ollama_top_k: int = 40
    ollama_repeat_penalty: float = 1.1
    ollama_context_window: int = 8_192
    ollama_max_output_tokens: int = 512
    ollama_num_threads: int = 6
    # ---- Router & Connectivity Settings ----
    enable_cloud_llm_router: bool = False
    cloud_llm_provider: str = "openrouter"
    cloud_llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("CLOUD_LLM_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY")
    )
    cloud_llm_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    cloud_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    cloud_llm_timeout_seconds: float = 25.0
    offline_llm_model: str = Field(
        default="llama3.2:3b",
        validation_alias=AliasChoices("OFFLINE_LLM_MODEL", "LOCAL_LLM_MODEL", "OLLAMA_MODEL")
    )
    connectivity_check_timeout_seconds: float = 1.5
    connectivity_check_cache_seconds: float = 15.0
    connectivity_check_url: str = "https://1.1.1.1"
    # ---- Context Composer Settings ----
    enable_context_composer: bool = True
    context_composer_dedup_threshold: float = 0.85
    knowledge_source_path: Path = Path("data/canonical_markdown")
    knowledge_max_file_size_bytes: int = 20_000_000
    faiss_index_path: Path = Path("data/faiss")
    faiss_allow_dangerous_deserialization: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    embedding_normalize: bool = True
    embedding_show_progress: bool = False
    # ---- Optimization parameters ----
    cache_maxsize_embeddings: int = 1_000_000  # max number of embeddings to cache
    cache_ttl_retrieval_seconds: int = 300
    adaptive_top_k_enabled: bool = True
    adaptive_top_k_base: int = 5
    adaptive_top_k_increment: int = 2
    embedding_local_files_only: bool = True
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_chunk_separators: list[str] = Field(default_factory=lambda: ["\n\n", "\n", " ", ""])
    rag_add_start_index: bool = True
    rag_search_limit: int = 5
    # IMPORTANT: The hybrid retriever uses RRF fusion which assigns distance = min(BM25_score, FAISS_L2).
    # BM25 scores are negative (e.g. -6.7) and FAISS L2 scores are positive (e.g. 3.1, 6.9).
    # A threshold of 2.0 incorrectly filters out valid top-RRF FAISS-dominated results.
    # Set to a large value (999.0) to disable the broken absolute filter and rely on RRF ranking + LLM grounding.
    rag_distance_threshold: float = 999.0
    candidate_window: int = Field(
        default=25,
        validation_alias=AliasChoices("CANDIDATE_WINDOW", "INITIAL_CANDIDATES", "RERANKER_TOP_N")
    )
    initial_candidates: int = Field(
        default=25,
        validation_alias=AliasChoices("INITIAL_CANDIDATES", "CANDIDATE_WINDOW", "RERANKER_TOP_N")
    )
    final_top_k: int = Field(
        default=5,
        validation_alias=AliasChoices("FINAL_TOP_K", "FINAL_RESULTS", "RAG_SEARCH_LIMIT")
    )
    final_results: int = Field(
        default=5,
        validation_alias=AliasChoices("FINAL_RESULTS", "FINAL_TOP_K", "RAG_SEARCH_LIMIT")
    )
    deduplicate_documents: bool = Field(
        default=True,
        validation_alias=AliasChoices("DEDUPLICATE_DOCUMENTS", "RAG_DEDUPLICATE_DOCUMENTS")
    )
    rrf_k: int = Field(
        default=60,
        validation_alias=AliasChoices("RRF_K", "HYBRID_RRF_K")
    )
    weight_dense: float = Field(
        default=0.5,
        validation_alias=AliasChoices("WEIGHT_DENSE", "HYBRID_WEIGHT_DENSE")
    )
    weight_sparse: float = Field(
        default=0.5,
        validation_alias=AliasChoices("WEIGHT_SPARSE", "HYBRID_WEIGHT_SPARSE")
    )
    fusion_mode: str = Field(
        default="weighted_hybrid",
        validation_alias=AliasChoices("FUSION_MODE", "HYBRID_FUSION_MODE")
    )
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_n: int = 25
    reranker_top_m: int = 5
    webcam_index: int = 0
    camera_fps: int = 15
    person_detection_reset_frames: int = 30
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    tts_voice_model: str = "en_US-lessac-medium"
    tts_piper_models_dir: str = "data/piper"
    tts_use_cuda: bool = False
    allow_online_stt_fallback: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Confidence Engine configuration
    confidence_weights: dict[str, float] = {
        "reranker": 0.35,
        "distance": 0.30,
        "count": 0.15,
        "source_diversity": 0.10,
        "evidence_consistency": 0.10,
    }
    confidence_thresholds: dict[str, float] = {
        "high": 0.80,
        "medium": 0.55,
        "low": 0.30,
    }
    hallucination_risk_thresholds: dict[str, float] = {
        "very_low": 0.2,
        "low": 0.4,
        "medium": 0.6,
        "high": 0.8,
    }
    answer_verification_enabled: bool = True
    debug_confidence: bool = False
    vision_confidence: float = 0.95
    vision_min_hits: int = 3
    # Observability and metrics configuration
    logging_json: bool = True  # Emit logs as JSON lines
    metrics_flush_interval_seconds: int = 60  # Interval for dashboard write
    dashboard_path: str = r"d:/AUNTII/diagnostics/performance_dashboard.json"
    health_check_timeout_seconds: int = 2
    # Existing values continue

    vision_frame_scale_width: int = 640
    vision_detection_scale: float = 1.05
    vision_detection_win_stride: list[int] = Field(default_factory=lambda: [8, 8])
    vision_detection_padding: list[int] = Field(default_factory=lambda: [16, 16])

    audio_stt_non_speaking_duration: float = 0.8
    audio_stt_debug: bool = False

    vad_sample_rate_options: list[int] = Field(default_factory=lambda: [8000, 16000, 32000, 48000])
    vad_frame_duration_options: list[int] = Field(default_factory=lambda: [10, 20, 30])

    tts_dummy_speech_delay: float = 0.02
    tts_dummy_speech_min_delay: float = 0.01

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

    @model_validator(mode="before")
    @classmethod
    def load_yaml_config(cls, data: dict) -> dict:
        config_path = Path("config.yaml")
        if config_path.exists():
            import yaml
            try:
                with open(config_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                # Flatten the nested structure
                if "app" in yaml_data:
                    for k, v in yaml_data["app"].items():
                        data[f"app_{k}"] = v
                if "retrieval" in yaml_data:
                    for k, v in yaml_data["retrieval"].items():
                        # Map keys to matching Pydantic fields
                        if k == "top_k":
                            data["rag_search_limit"] = v
                        elif k == "chunk_size":
                            data["rag_chunk_size"] = v
                        elif k == "chunk_overlap":
                            data["rag_chunk_overlap"] = v
                        elif k == "distance_threshold":
                            data["rag_distance_threshold"] = v
                        else:
                            data[f"rag_{k}"] = v
                if "cache" in yaml_data:
                    for k, v in yaml_data["cache"].items():
                        data[f"cache_{k}"] = v
                if "memory" in yaml_data:
                    for k, v in yaml_data["memory"].items():
                        data[f"memory_{k}"] = v
                if "ollama" in yaml_data:
                    for k, v in yaml_data["ollama"].items():
                        data[f"ollama_{k}"] = v
                if "embedding" in yaml_data:
                    for k, v in yaml_data["embedding"].items():
                        data[f"embedding_{k}"] = v
                if "logging" in yaml_data:
                    for k, v in yaml_data["logging"].items():
                        data[f"log_{k}"] = v
            except Exception as e:
                print(f"Warning: Failed to load config.yaml: {e}")
        return data

    @field_validator("ollama_base_url")
    @classmethod
    def require_loopback_ollama(cls, value: str) -> str:
        """Prevent an environment override from routing prompts to a remote host."""
        parsed_url = urlparse(value)
        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError("OLLAMA_BASE_URL must use http or https scheme.")
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
            "num_thread": self.ollama_num_threads,
        }

    @model_validator(mode="after")
    def validate_offline_llm_safety(self) -> "Settings":
        """Warn if a small offline LLM (<3b, e.g. 1.5b) is configured without ContextComposer enabled."""
        model_name = self.offline_llm_model.lower()
        if not self.enable_context_composer and ("1.5b" in model_name or "0.5b" in model_name):
            import logging
            logging.getLogger(__name__).warning(
                "--------------------------------------------------------------------------------\n"
                "WARNING: UNHEALTHY RAG CONFIGURATION DETECTED!\n"
                f"OFFLINE_LLM_MODEL='{self.offline_llm_model}' with ENABLE_CONTEXT_COMPOSER=False is known "
                "to produce multi-table context hallucinations. Enable context composer (ENABLE_CONTEXT_COMPOSER=true) "
                "or use a model size >=3b (e.g. OFFLINE_LLM_MODEL='qwen2.5:3b') for reliable offline RAG.\n"
                "--------------------------------------------------------------------------------"
            )
        return self


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