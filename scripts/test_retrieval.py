"""Test script to evaluate RAG retrieval and response generation."""

import logging
from pathlib import Path

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker

logger = logging.getLogger(__name__)

QUESTIONS = [
    "What is the fee structure for BE programs?",
    "Who is the current Vice Chancellor?",
    "What placement companies recruit from this college?",
    "What is the admission process for BCA?",
    "Tell me about the hostel facilities.",
]


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=settings.embedding_show_progress,
        local_files_only=settings.embedding_local_files_only,
    )
    similarity_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=settings.faiss_index_path,
        allow_dangerous_deserialization=settings.faiss_allow_dangerous_deserialization,
        embedding_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )
    markdown_loader = MarkdownKnowledgeLoader(
        knowledge_source_path=settings.knowledge_source_path,
        max_file_size_bytes=settings.knowledge_max_file_size_bytes,
    )
    text_chunker = SemanticDocumentChunker(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=settings.rag_chunk_separators,
        add_start_index=settings.rag_add_start_index,
    )

    from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
    from campus_helpdesk.infrastructure.llm.factory import create_llm_service
    from campus_helpdesk.infrastructure.rag.context_composer import ContextComposer

    rag_pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        rag_pipeline.load_index()

    llm_service = create_llm_service(settings)
    context_composer = ContextComposer(settings=settings)

    chat_service = RAGChatService(
        llm_service=llm_service,
        rag_pipeline=rag_pipeline,
        context_composer=context_composer,
    )

    print("\n" + "=" * 80)
    print("STARTING RETRIEVAL & RESPONSE GENERATION TEST")
    print("=" * 80 + "\n")

    for i, question in enumerate(QUESTIONS, start=1):
        print(f"\n--- QUESTION {i}: {question} ---")
        
        raw_results = rag_pipeline.search(question)
        search_results = context_composer.compose(raw_results)
        print(f"Retrieved {len(raw_results)} chunk(s) -> Composed {len(search_results)} source chunk(s) (Deduplicated):")
        for idx, res in enumerate(search_results, start=1):
            doc = res.document
            source = doc.metadata.get("source_filename") or doc.metadata.get("source") or doc.metadata.get("file_path") or "unknown"
            snippet = doc.content.strip().replace("\n", " ")[:150]
            print(f"  [{idx}] Source: {source} | Distance: {res.distance:.4f}")
            print(f"      Snippet: {snippet}...")

        # Get response from chat_service
        result = chat_service.respond(question)
        print(f"\nAnswer:\n{result.reply}")
        if result.supporting_sources:
            print("\nSupporting Sources reported by ChatResult:")
            for src in result.supporting_sources:
                print(f"  - {src}")
        print("\n" + "-" * 80)


if __name__ == "__main__":
    main()
