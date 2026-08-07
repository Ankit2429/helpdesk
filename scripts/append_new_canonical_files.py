"""
Append New Canonical Markdown Policies to FAISS Store
======================================================
Loads existing production FAISS index at data/faiss.
Ingests:
1. data/canonical_markdown/placements/placements_policy_canonical.md
2. data/canonical_markdown/hostel/hostel_rules_and_facilities_canonical.md
Saves the updated FAISS index.
"""

from pathlib import Path
from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.knowledge_loader import KnowledgeLoader
from campus_helpdesk.infrastructure.rag.semantic_chunker import SemanticDocumentChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

ROOT_DIR = Path(__file__).resolve().parent.parent
FAISS_DIR = ROOT_DIR / "data" / "faiss"

TARGET_FILES = [
    ROOT_DIR / "data" / "canonical_markdown" / "placements" / "placements_policy_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "hostel" / "hostel_rules_and_facilities_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "admissions" / "admissions_transfer_entrance_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "facilities" / "library_services_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "fees" / "fee_and_scholarships_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "administration" / "it_admin_policies_canonical.md",
    ROOT_DIR / "data" / "canonical_markdown" / "facilities" / "campus_facilities_canonical.md",
]

def append_canonical():
    print("=======================================================================")
    print("  INGESTING NEW CANONICAL POLICIES INTO EXISTING FAISS STORE")
    print("=======================================================================")

    s = get_settings()

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

    faiss_store.load()

    loader = KnowledgeLoader(
        knowledge_source_path=ROOT_DIR / "data" / "canonical_markdown",
        max_file_size_bytes=getattr(s, "knowledge_max_file_size_bytes", 10 * 1024 * 1024),
    )
    chunker = SemanticDocumentChunker(chunk_size=800, chunk_overlap=200)

    total_added = 0
    for target in TARGET_FILES:
        if not target.exists():
            print(f"[WARN] File not found: {target}")
            continue

        docs = loader.load(target)
        rel_path = str(target.relative_to(ROOT_DIR / "data" / "canonical_markdown"))
        for doc in docs:
            doc.metadata["source"] = rel_path
            doc.metadata["source_filename"] = target.name
            doc.metadata["category"] = target.parent.name

        chunks = chunker.split(docs)
        faiss_store.add(chunks)
        total_added += len(chunks)
        print(f"[ADDED] {target.name}: {len(chunks)} chunks")

    faiss_store.save()
    print("\n=======================================================================")
    print(f"  SUCCESSFULLY INGESTED {total_added} NEW CHUNKS INTO FAISS STORE")
    print(f"  Index Path: {FAISS_DIR}")
    print("=======================================================================")

if __name__ == "__main__":
    append_canonical()
