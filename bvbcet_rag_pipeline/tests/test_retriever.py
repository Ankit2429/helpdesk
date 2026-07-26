"""Unit tests for ChromaRetriever RAG engine."""

import json
from pathlib import Path
import shutil
import tempfile
import numpy as np
from langchain_core.documents import Document

from vector_db.chroma_builder import ChromaBuilder
from retrieval.retriever import ChromaRetriever


def test_chroma_retriever_workflow():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        jsonl_path = temp_dir / "chunks.jsonl"
        npy_path = temp_dir / "embeddings.npy"
        persist_dir = temp_dir / "chroma"

        # Create dummy records
        records = [
            {
                "text": "The computer science department offers B.E. in Artificial Intelligence.",
                "metadata": {
                    "id": "chunk_cs_01",
                    "title": "Computer Science Department",
                    "heading": "Programs Offered",
                    "category": "departments",
                    "source_filename": "computer_science.md",
                    "relative_file_path": "markdown/departments/computer_science.md",
                },
            },
            {
                "text": "Admissions for KCET quota candidates start in July.",
                "metadata": {
                    "id": "chunk_adm_01",
                    "title": "Admissions 2025",
                    "heading": "KCET Quota",
                    "category": "admissions",
                    "source_filename": "admissions.md",
                    "relative_file_path": "markdown/admissions/admissions.md",
                },
            },
        ]

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        # Initialize small embedding model for testing
        retriever = ChromaRetriever(
            model_name="all-MiniLM-L6-v2",
            persist_dir=persist_dir,
            collection_name="test_retrieval_knowledge",
        )

        # Generate actual embeddings using model
        vec1 = retriever.embed_question(records[0]["text"])
        vec2 = retriever.embed_question(records[1]["text"])
        embeddings_matrix = np.array([vec1, vec2], dtype=np.float32)
        np.save(npy_path, embeddings_matrix)

        # Build index in ChromaDB
        builder = ChromaBuilder(
            persist_dir=persist_dir,
            collection_name="test_retrieval_knowledge",
        )
        builder.build_index(jsonl_path=jsonl_path, embeddings_path=npy_path)

        # Test retrieval
        docs = retriever.retrieve(
            question="What programs are offered in computer science?",
            top_k=2,
        )

        assert len(docs) > 0
        assert isinstance(docs[0], Document)
        assert "score" in docs[0].metadata
        assert docs[0].metadata["category"] in ["departments", "admissions"]

        # Test Category Filter
        filtered_docs = retriever.retrieve(
            question="KCET quota admissions",
            category="admissions",
            top_k=5,
        )
        assert len(filtered_docs) == 1
        assert filtered_docs[0].metadata["category"] == "admissions"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
