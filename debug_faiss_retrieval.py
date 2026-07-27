"""
debug_faiss_retrieval.py
Logs the exact retrieved text chunks, similarity scores, and prompts for Q2 and Q3
to isolate whether failure is due to FAISS retrieval or LLM model unfaithfulness.
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from ttt_service import TTTService


def inspect_query(service: TTTService, model_name: str, query: str):
    print(f"\n" + "=" * 80)
    print(f"  INSPECTING QUERY [{model_name}]: \"{query}\"")
    print("=" * 80)

    rag = service.rag_service
    if rag is None or not hasattr(rag, "_rag_pipeline"):
        print("ERROR: RAG pipeline not initialized!")
        return

    # 1. Retrieve chunks directly from FAISS
    chunks = rag._rag_pipeline.search(query)
    print(f"Found {len(chunks)} retrieved chunks from FAISS:")
    for idx, chunk in enumerate(chunks, 1):
        content = getattr(chunk.document, "content", str(chunk.document))
        dist = getattr(chunk, "distance", "N/A")
        print(f"\n--- Chunk #{idx} (FAISS Distance Score: {dist}) ---")
        print(content)

    # 2. Get LLM response
    print("\n" + "-" * 80)
    response = rag.respond(query)
    print(f"LLM Response ({model_name}): \"{response.reply}\"")
    print("-" * 80)


def main():
    service = TTTService()
    current_model = service.rag_service._llm_service._model if service.rag_service and hasattr(service.rag_service, "_llm_service") else "unknown"
    
    inspect_query(service, current_model, "When is the library open?")
    inspect_query(service, current_model, "What are the library hours on weekends?")


if __name__ == "__main__":
    main()
