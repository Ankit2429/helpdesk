#!/usr/bin/env python3
"""
rebuild_faiss_store.py
Rebuilds the production FAISS index at data/faiss from chunks.jsonl
using FAISSSimilarityStore and SentenceTransformerEmbeddings.
"""

import os
import sys
import json
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

def main():
    settings = Settings()
    chunks_path = Path("chunks.jsonl")
    if not chunks_path.exists():
        print(f"Error: {chunks_path} not found.")
        sys.exit(1)

    print("Loading chunks from chunks.jsonl...")
    docs = []
    with open(chunks_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                text = item.get("text", "")
                if not text.strip():
                    continue
                metadata = {
                    "source": str(item.get("source", "")),
                    "title": str(item.get("title", "")),
                    "category": str(item.get("category", "")),
                    "subcategory": str(item.get("subcategory", "")),
                    "department": str(item.get("department", "")),
                    "campus": str(item.get("campus", "")),
                    "document_type": str(item.get("document_type", "")),
                    "headings": ", ".join(item.get("headings", [])),
                }
                docs.append(KnowledgeDocument(content=text, metadata=metadata))

    print(f"Loaded {len(docs)} knowledge documents.")

    print("Initializing SentenceTransformerEmbeddings...")
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=True,
        local_files_only=settings.embedding_local_files_only,
    )

    faiss_path = Path("data/faiss")
    faiss_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=faiss_path,
        allow_dangerous_deserialization=True,
        embedding_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )

    print(f"Building and saving FAISS store to {faiss_path}...")
    faiss_store.add(docs)
    faiss_store.save()
    print("Successfully rebuilt and saved FAISS store to data/faiss!")

if __name__ == "__main__":
    main()
