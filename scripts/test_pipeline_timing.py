"""Pipeline Latency & Performance Instrumentation Test."""

import logging
import sys
import time
from pathlib import Path

from campus_helpdesk.application.rag_chat_service import RAGChatService
from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.config.logging import configure_logging
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.audio.tts_service import NonBlockingTTSService
from campus_helpdesk.infrastructure.llm.ollama_service import OllamaLLMService
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.markdown_loader import MarkdownKnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import (
    SentenceTransformerEmbeddings,
)
from campus_helpdesk.services.language_detector import LanguageDetector

logging.basicConfig(level=logging.WARNING)

TEST_QUESTIONS = [
    {"lang": "en", "label": "English", "q": "What is the fee structure for BE courses?"},
    {"lang": "en", "label": "English", "q": "Who is the Vice Chancellor?"},
    {"lang": "hi", "label": "Hindi", "q": "बीई पाठ्यक्रम की फीस कितनी है?"},
    {"lang": "hi", "label": "Hindi", "q": "वर्तमान कुलपति कौन हैं?"},
    {"lang": "kn", "label": "Kannada", "q": "ಬಿಸಿಎ ಕೋರ್ಸ್‌ಗೆ ಸೇರಲು ಪ್ರವೇಶ ಅರ್ಹತೆಗಳು ಯಾವುವು?"},
    {"lang": "kn", "label": "Kannada", "q": "ಹಾಸ್ಟೆಲ್ ಸೌಲಭ್ಯಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ."},
]


def measure_detailed_turn(
    question: str,
    chat_service: RAGChatService,
    tts_service: NonBlockingTTSService,
    llm_service: OllamaLLMService,
    rag_pipeline: RAGPipeline,
    session_id: str,
) -> dict:
    t_start = time.perf_counter()

    # 1. Language Detection Timing
    t0 = time.perf_counter()
    det = LanguageDetector.detect(question)
    t_lang_detect = (time.perf_counter() - t0) * 1000.0

    # 2. Query Translation (if non-English)
    t_query_trans = 0.0
    search_q = question
    if det.language != "en":
        t0 = time.perf_counter()
        tr_prompt = (
            f"Translate the following question into a 1-sentence English search query (keywords only):\n"
            f"Question: {question}\n"
            f"English Search Query:"
        )
        try:
            search_q = llm_service.generate(tr_prompt).strip().split("\n")[0]
        except Exception:
            search_q = question
        t_query_trans = (time.perf_counter() - t0) * 1000.0

    # 3. RAG Vector Search & Retrieval
    t0 = time.perf_counter()
    search_results = rag_pipeline.search(search_q)
    t_rag_search = (time.perf_counter() - t0) * 1000.0

    # 4. LLM Answer Generation
    t0 = time.perf_counter()
    chat_res = chat_service.respond(question, session_id=session_id)
    t_llm_gen = (time.perf_counter() - t0) * 1000.0

    # Subtract pre-translation time if it was measured inside chat_service.respond
    if t_query_trans > 0:
        t_llm_gen = max(0.0, t_llm_gen - t_query_trans)

    # 5. TTS Synthesis Timing
    t0 = time.perf_counter()
    tts_service.speak(chat_res.reply, language=chat_res.detected_language)
    tts_service.wait_until_done(timeout=10.0)
    t_tts_synth = (time.perf_counter() - t0) * 1000.0

    t_total = (time.perf_counter() - t_start) * 1000.0

    return {
        "question": question,
        "language_label": det.language_name,
        "language_code": chat_res.detected_language,
        "reply": chat_res.reply,
        "sources": chat_res.supporting_sources,
        "t_lang_detect": t_lang_detect,
        "t_query_trans": t_query_trans,
        "t_rag_search": t_rag_search,
        "t_llm_gen": t_llm_gen,
        "t_tts_synth": t_tts_synth,
        "t_total": t_total,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    settings = get_settings()

    print("\n" + "=" * 85)
    print("DETAILED PIPELINE LATENCY & PERFORMANCE TIMING BENCHMARK")
    print("=" * 85 + "\n")

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
    rag_pipeline = RAGPipeline(
        document_loader=markdown_loader,
        document_chunker=text_chunker,
        similarity_store=similarity_store,
        search_limit=settings.rag_search_limit,
    )
    rag_pipeline.load_index()

    llm_service = OllamaLLMService(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        generation_options=settings.ollama_options,
    )
    chat_service = RAGChatService(llm_service=llm_service, rag_pipeline=rag_pipeline)
    tts_service = NonBlockingTTSService(piper_models_dir=settings.tts_piper_models_dir)

    print(f"{'Turn / Question':<38} | {'Lang':<5} | {'Detect':<7} | {'Translate':<9} | {'RAG Search':<10} | {'LLM Gen':<9} | {'TTS Synth':<9} | {'TOTAL':<9}")
    print("-" * 115)

    session_id = "timing_session"

    for idx, item in enumerate(TEST_QUESTIONS, start=1):
        q_short = item['q'][:35] + "..." if len(item['q']) > 35 else item['q']
        res = measure_detailed_turn(
            item["q"],
            chat_service,
            tts_service,
            llm_service,
            rag_pipeline,
            session_id,
        )

        detect_str = f"{res['t_lang_detect']:.1f}ms"
        trans_str = f"{res['t_query_trans']:.1f}ms" if res["t_query_trans"] > 0 else "0.0ms (N/A)"
        search_str = f"{res['t_rag_search']:.1f}ms"
        gen_str = f"{res['t_llm_gen']:.1f}ms"
        tts_str = f"{res['t_tts_synth']:.1f}ms"
        total_str = f"{res['t_total']/1000.0:.2f}s"

        print(f"#{idx} {q_short:<34} | {res['language_code'].upper():<5} | {detect_str:<7} | {trans_str:<9} | {search_str:<10} | {gen_str:<9} | {tts_str:<9} | {total_str:<9}")

    print("-" * 115 + "\n")


if __name__ == "__main__":
    main()
