"""Interactive CLI for the Campus Helpdesk RAG Chatbot."""

import logging
import sys
from pathlib import Path

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)

logger = logging.getLogger(__name__)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = get_settings()
    configure_logging("WARNING")

    print("Initializing Campus Helpdesk Chatbot...")

    from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
    rag_pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        try:
            rag_pipeline.load_index()
            print("Loaded vector store index successfully.")
        except Exception as err:
            print(f"Warning: Could not load vector store index: {err}")

    from campus_helpdesk.infrastructure.llm.factory import create_llm_service
    llm_service = create_llm_service(settings)

    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
    )

    session_id = "cli_session"

    print("\n" + "=" * 60)
    print("Campus Helpdesk Assistant ready! Type 'exit' or 'quit' to end.")
    print("=" * 60 + "\n")

    lang_map = {"en": "English", "hi": "Hindi", "kn": "Kannada"}

    # If arguments are passed on command line, process them sequentially to simulate a multi-turn conversation
    if len(sys.argv) > 1:
        inputs = sys.argv[1:]
        for user_input in inputs:
            print(f"You: {user_input}")
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            try:
                result = chat_service.respond(user_input, session_id=session_id)
                lang_disp = lang_map.get(result.detected_language, result.detected_language.upper())
                print(f"[Detected Language: {lang_disp} ({result.detected_language.upper()})]")
                print(f"Assistant: {result.reply}\n")
                if result.supporting_sources:
                    print("Retrieved Sources:")
                    for src in result.supporting_sources:
                        print(f"  - {src}")
                    print()
            except Exception as exc:
                print(f"[Error processing request: {exc}]\n")
        return

    # Standard interactive loop
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            result = chat_service.respond(user_input, session_id=session_id)
            lang_disp = lang_map.get(result.detected_language, result.detected_language.upper())
            print(f"\n[Detected Language: {lang_disp} ({result.detected_language.upper()})]")
            print(f"Assistant: {result.reply}\n")
            if result.supporting_sources:
                print("Retrieved Sources:")
                for src in result.supporting_sources:
                    print(f"  - {src}")
                print()
        except Exception as exc:
            print(f"\n[Error processing request: {exc}]\n")


if __name__ == "__main__":
    main()
