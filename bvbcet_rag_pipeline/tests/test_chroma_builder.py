"""Unit tests for ChromaBuilder vector store manager."""

import json
from pathlib import Path
import shutil
import tempfile
import numpy as np

from vector_db.chroma_builder import ChromaBuilder


def test_chroma_builder_workflow():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        jsonl_path = temp_dir / "chunks.jsonl"
        npy_path = temp_dir / "embeddings.npy"
        persist_dir = temp_dir / "chroma"

        # Create dummy JSONL chunks
        records = [
            {
                "text": "The computer science department offers B.E. and M.Tech programs.",
                "metadata": {
                    "id": "chunk_cs_01",
                    "title": "Computer Science Department",
                    "heading": "Programs Offered",
                    "level": 2,
                    "category": "departments",
                    "source_filename": "computer_science.md",
                    "relative_file_path": "markdown/departments/computer_science.md",
                },
            },
            {
                "text": "Admissions for undergraduate KCET quota begin in June.",
                "metadata": {
                    "id": "chunk_adm_01",
                    "title": "Admissions 2025",
                    "heading": "KCET Quota",
                    "level": 2,
                    "category": "admissions",
                    "source_filename": "admissions.md",
                    "relative_file_path": "markdown/admissions/admissions.md",
                },
            },
        ]

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        # Create dummy embeddings array (2 vectors of dimension 384)
        dummy_embeddings = np.random.rand(2, 384).astype(np.float32)
        np.save(npy_path, dummy_embeddings)

        builder = ChromaBuilder(
            persist_dir=persist_dir,
            collection_name="test_bvbcet_knowledge",
            batch_size=2,
        )

        vectors_stored = builder.build_index(
            jsonl_path=jsonl_path,
            embeddings_path=npy_path,
        )

        assert vectors_stored == 2
        assert builder.collection.count() == 2

        # Test querying collection
        res = builder.collection.query(
            query_embeddings=[dummy_embeddings[0].tolist()],
            n_results=1,
        )
        assert len(res["ids"][0]) == 1
        assert res["ids"][0][0] == "chunk_cs_01"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
