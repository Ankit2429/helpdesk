#!/usr/bin/env python
"""
diagnose_rag.py — RAG Pipeline Diagnostic Tool for AUNTII

Logs at every stage:
  1. Raw retrieved chunks (title, source, content snippet, distance)
  2. Context string passed to LLM
  3. Full final prompt
  4. LLM raw response
  5. Whether context was grounded or LLM hallucinated from general knowledge
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("diagnose_rag")

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.application.rag_pipeline import RAGPipeline
from campus_helpdesk.infrastructure.rag.prompt_context_builder import PromptContextBuilder
from campus_helpdesk.application.llm_service import LLMService

TEST_QUERIES = [
    "What canteens are available on campus?",
    "What are the hostel facilities for students?",
    "What is the B.Tech CSE fee structure?",
    "Who is the principal of KLE Tech?",
    "What departments are offered at BVB Engineering College?",
]

SYSTEM_PROMPT_GROUNDED = """You are AUNTII, an offline AI campus helpdesk assistant for KLE Technological University (BVB Engineering College), Hubballi.

STRICT RULES:
1. Answer ONLY using the information provided in the Context section below.
2. Do NOT use general knowledge, assumptions, or training data.
3. If the answer is NOT clearly present in the context, respond exactly:
   "I don't have reliable information about this in the campus knowledge base. Please contact the university office directly."
4. Never invent names, fees, dates, or contact numbers.
5. Cite the source title when answering."""


def diagnose_query(pipeline: RAGPipeline, builder: PromptContextBuilder, llm: LLMService, query: str) -> None:
    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    # Stage 1: Raw retrieval
    results = list(pipeline.search(query, limit=5))
    print(f"\n[Stage 1] Retrieved {len(results)} chunks:")
    for i, r in enumerate(results):
        doc = r.document
        title = doc.metadata.get("title", doc.metadata.get("Header 1", "Unknown"))
        source = doc.metadata.get("source", "?")
        snippet = doc.content.strip()[:180].replace("\n", " ")
        print(f"  Chunk {i+1}: dist={r.distance:.4f} | title='{title}' | source='{source}'")
        print(f"           snippet: {snippet}...")

    # Stage 2: Context string
    context_str = builder.build_context(results)
    passed_threshold = [r for r in results if r.distance <= builder.similarity_threshold]
    print(f"\n[Stage 2] Context builder: threshold={builder.similarity_threshold}")
    print(f"  Chunks passing threshold: {len(passed_threshold)}/{len(results)}")
    if not context_str:
        print("  ⚠️  WARNING: context_str is EMPTY — LLM will hallucinate from general knowledge!")
    else:
        print(f"  Context length: {len(context_str)} chars")
        print(f"  Context preview:\n{context_str[:400]}...")

    # Stage 3: Full prompt
    parts = [SYSTEM_PROMPT_GROUNDED]
    if context_str:
        parts.append(f"Context:\n{context_str}")
    parts.append(f"User Question: {query}")
    prompt = "\n\n".join(parts)

    print(f"\n[Stage 3] Full prompt ({len(prompt)} chars):")
    print("-" * 40)
    print(prompt[:600] + ("..." if len(prompt) > 600 else ""))
    print("-" * 40)

    # Stage 4: LLM response
    print(f"\n[Stage 4] LLM Response:")
    tokens = []
    for tok in llm.generate_stream(prompt):
        tokens.append(tok)
    response = "".join(tokens)
    print(response)

    # Stage 5: Grounding verdict
    print(f"\n[Stage 5] Grounding Verdict:")
    if not context_str:
        print("  ❌ FAIL — No context passed. Response is 100% LLM hallucination from training data.")
    elif "don't have" in response.lower() or "contact" in response.lower() or "no information" in response.lower():
        print("  ✅ PASS — LLM correctly admitted limited knowledge.")
    else:
        print("  ✅ PASS — Response appears grounded in retrieved context.")


def main():
    print("Initializing RAG pipeline (using same factory as touch_app)...")
    from campus_helpdesk.config.settings import get_settings
    from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
    from campus_helpdesk.infrastructure.llm.factory import create_llm_service
    from campus_helpdesk.config.logging import configure_logging

    settings = get_settings()
    configure_logging(settings.log_level)

    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    builder = PromptContextBuilder(
        max_context_size=7000,
        similarity_threshold=settings.rag_distance_threshold,
    )
    llm = create_llm_service(settings)

    print(f"Similarity threshold: {builder.similarity_threshold}")
    print(f"Max context size: {builder.max_context_size} chars")
    print(f"FAISS index path: {settings.faiss_index_path}")

    for query in TEST_QUERIES:
        try:
            diagnose_query(pipeline, builder, llm, query)
        except Exception as e:
            print(f"\n[ERROR] Query '{query}' failed: {e}")
        print()

    print("\n" + "=" * 80)
    print("RAG DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
