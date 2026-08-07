"""
Rebuild FAISS Vector Store and Index from Canonical Markdown Knowledge Base
=============================================================================

Scans `data/canonical_markdown/` (including newly added canonical placement and hostel policies).
Uses `SemanticDocumentChunker` with header propagation and 200-char block overlap.
Generates FAISS dense vector store at `data/faiss`.
"""

import time
from pathlib import Path

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

ROOT_DIR = Path(__file__).resolve().parent.parent
CANONICAL_DIR = ROOT_DIR / "data" / "canonical_markdown"
FAISS_DIR = ROOT_DIR / "data" / "faiss"

def rebuild():
    print("=======================================================================")
    print("  REBUILDING FAISS & BM25 INDEXES FROM CANONICAL MARKDOWN KNOWLEDGE")
    print("=======================================================================")

    t0 = time.perf_counter()
    s = get_settings()

    loader = KnowledgeLoader(
        knowledge_source_path=CANONICAL_DIR,
        max_file_size_bytes=getattr(s, "knowledge_max_file_size_bytes", 10 * 1024 * 1024),
    )
    chunker = SemanticDocumentChunker(chunk_size=800, chunk_overlap=200)

    # 1. Discover all .md files in data/canonical_markdown/
    md_files = list(CANONICAL_DIR.rglob("*.md"))
    print(f"Discovered {len(md_files)} canonical Markdown documents.")

    all_chunks = []
    for file_path in md_files:
        try:
            rel_path = str(file_path.relative_to(CANONICAL_DIR))
            docs = loader.load(file_path)
            # Add relative source metadata
            for doc in docs:
                doc.metadata["source"] = rel_path
                doc.metadata["source_filename"] = file_path.name
                doc.metadata["category"] = file_path.parent.name

            chunks = chunker.split(docs)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"[WARN] Error loading {file_path.name}: {e}")

    print(f"Generated {len(all_chunks)} semantic chunks from canonical knowledge base.")

    # 2. Build FAISS Vector Index
    embeddings = SentenceTransformerEmbeddings(
        model_name=s.embedding_model,
        device=s.embedding_device,
        batch_size=s.embedding_batch_size,
        normalize_embeddings=s.embedding_normalize,
        show_progress=True,
        local_files_only=s.embedding_local_files_only,
    )

    faiss_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=FAISS_DIR,
        allow_dangerous_deserialization=True,
        embedding_metadata={
            "embedding_model": s.embedding_model,
            "embedding_normalize": s.embedding_normalize,
        },
    )

    faiss_store.reset()
    faiss_store.add(all_chunks)
    faiss_store.save()

    t_elapsed = time.perf_counter() - t0
    print("\n=======================================================================")
    print(f"  FAISS REBUILD COMPLETE: {len(all_chunks)} chunks indexed in {t_elapsed:.2f}s")
    print(f"  Index Path: {FAISS_DIR}")
    print("=======================================================================")

if __name__ == "__main__":
    rebuild()
