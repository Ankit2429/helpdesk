#!/usr/bin/env python
"""Campus Helpdesk CLI entry point.

Provides an interactive command-line chat that orchestrates the existing
RAG pipeline without duplicating any logic.  The implementation relies on
the production-ready components in the `campus_helpdesk` package:

* **Configuration** - `campus_helpdesk.config.settings.get_settings`
* **LLM wrapper** - `OllamaLLMService`
* **Retriever / Reranker** - wired via `create_rag_pipeline`
* **Conversation management** - `SessionManager` (used by `RAGChatService`)

Supported CLI commands:
    /exit, /quit      - terminate the session
    /help             - show this help message
    /clear            - clear conversation history
    /history          - display recent dialogue turns
    /stats            - show basic configuration statistics
    /debug            - toggle debug mode (extra logging)
    /reload           - reload the RAG index and recreate services
    /health           - perform a lightweight health check
"""

import logging

from campus_helpdesk.application.rag_chat_service import RAGChatService  # type: ignore
from campus_helpdesk.application.session_manager import SessionManager  # type: ignore
from campus_helpdesk.config.settings import Settings, get_settings  # type: ignore
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService  # type: ignore
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level configuration (loaded once at import time)
# ---------------------------------------------------------------------------
_SETTINGS: Settings = get_settings()
_DEBUG: bool = _SETTINGS.debug

def _configure_logging() -> None:
    level = logging.DEBUG if _DEBUG else getattr(logging, _SETTINGS.log_level.upper(), logging.INFO)
    # basicConfig is a no-op after the first call, so we must also
    # update the root logger level directly for runtime /debug toggles.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(level)


def _create_services() -> RAGChatService:
    """Instantiate the LLM service, RAG pipeline and chat service.

    OllamaLLMService.__init__ signature:
        base_url, model, timeout_seconds, generation_options, [client]

    generation_options is a dict of Ollama generation parameters.
    All values come from Settings to avoid hardcoding.
    """
    s = _SETTINGS
    generation_options = {
        "temperature": s.ollama_temperature,
        "top_p": s.ollama_top_p,
        "top_k": s.ollama_top_k,
        "repeat_penalty": s.ollama_repeat_penalty,
        "num_ctx": s.ollama_context_window,
        "num_predict": s.ollama_max_output_tokens,
        "num_thread": s.ollama_num_threads,
    }
    llm_service = OllamaLLMService(
        base_url=s.ollama_base_url,
        model=s.ollama_model,
        timeout_seconds=s.ollama_timeout_seconds,
        generation_options=generation_options,
    )
    rag_pipeline = create_rag_pipeline(s)
    return RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        session_manager=SessionManager(
            ttl_seconds=7200,
            max_history_turns=s.rag_search_limit,
        ),
    )


# ---------------------------------------------------------------------------
# Lazy service singleton – reset by /reload
# ---------------------------------------------------------------------------
_chat_service: RAGChatService | None = None


def _ensure_chat_service() -> RAGChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = _create_services()
    return _chat_service


# ---------------------------------------------------------------------------
# Slash-command handlers
# ---------------------------------------------------------------------------

def _health_check() -> bool:
    """Return True if the RAG pipeline initialises without error."""
    try:
        service = _ensure_chat_service()
        if hasattr(service._rag_pipeline, "load_index"):
            service._rag_pipeline.load_index()
        logger.info("Health check passed - RAG pipeline is ready.")
        return True
    except Exception as exc:  # pragma: no cover
        logger.error("Health check failed: %s", exc)
        return False


def _print_help() -> None:
    print(
        "\nAvailable commands:\n"
        "  /exit, /quit   - End the interactive session.\n"
        "  /help          - Show this help message.\n"
        "  /clear         - Clear conversation history.\n"
        "  /history       - Show recent dialogue turns.\n"
        "  /stats         - Display basic configuration statistics.\n"
        "  /debug         - Toggle debug logging.\n"
        "  /reload        - Reload the RAG index and recreate services.\n"
        "  /health        - Run a quick health check.\n"
    )


def _toggle_debug() -> None:
    global _DEBUG
    _DEBUG = not _DEBUG
    _SETTINGS.debug = _DEBUG
    _configure_logging()
    print(f"Debug mode {'enabled' if _DEBUG else 'disabled'}.")


def _show_stats() -> None:
    s = _SETTINGS
    print(
        f"\nCurrent configuration:\n"
        f"  LLM model       : {s.ollama_model}\n"
        f"  Embedding model : {s.embedding_model}\n"
        f"  RAG search limit: {s.rag_search_limit}\n"
        f"  Reranker enabled: {s.reranker_enabled}\n"
        f"  Debug           : {s.debug}\n"
    )


def _clear_history() -> None:
    service = _ensure_chat_service()
    service.clear_history(session_id="cli")
    print("Conversation history cleared.")


def _show_history() -> None:
    service = _ensure_chat_service()
    memory = service.session_manager.get_or_create_session("cli")
    messages = memory.get_messages()
    if not messages:
        print("[No history]")
        return
    for idx, msg in enumerate(messages, 1):
        role = msg["role"].capitalize()
        print(f"{idx}. {role}: {msg['content']}")


def _reload_services() -> None:
    global _chat_service
    _chat_service = None
    _ensure_chat_service()
    print("Services reloaded.")


def _process_command(command: str) -> bool:
    """Execute a slash command.

    Returns True to keep the loop running, False to exit.
    """
    cmd = command.strip().lower()
    if cmd in ("/exit", "/quit"):
        print("Good-bye!")
        return False
    if cmd == "/help":
        _print_help()
    elif cmd == "/clear":
        _clear_history()
    elif cmd == "/history":
        _show_history()
    elif cmd == "/stats":
        _show_stats()
    elif cmd == "/debug":
        _toggle_debug()
    elif cmd == "/reload":
        _reload_services()
    elif cmd == "/health":
        ok = _health_check()
        print("Health check", "OK" if ok else "FAILED")
    else:
        print(f"Unknown command: {command!r}. Type /help for a list of commands.")
    return True


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _configure_logging()
    print("Campus Helpdesk Chat - type /help for commands, /exit to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if not _process_command(user_input):
                break
            continue

        try:
            service = _ensure_chat_service()
            result = service.respond(user_input, session_id="cli")
            print(f"\nAssistant: {result.reply}\n")
            if _DEBUG:
                print(f"[Debug] Confidence: {result.confidence_score} ({result.confidence_level})")
                if result.supporting_sources:
                    print("[Debug] Sources:", ", ".join(result.supporting_sources))
        except Exception as exc:  # pragma: no cover
            logger.exception("Error during chat response")
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
