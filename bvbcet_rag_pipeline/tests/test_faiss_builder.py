"""Unit tests for FAISSBuilder vector database manager."""

import json
from pathlib import Path
import shutil
import tempfile
import numpy as np

from vector_db.faiss_builder import FAISSBuilder


def test_faiss_builder_workflow():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        npy_path = temp_dir / "embeddings.npy"
        json_path = temp_dir / "metadata.json"
        persist_dir = temp_dir / "faiss"

        # Create dummy metadata records
        records = [
            {"id": "chunk_01", "title": "Civil Engineering", "category": "departments"},
            {"id": "chunk_02", "title": "Hostel Regulations", "category": "hostel"},
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f)

        # Create dummy embeddings array (2 vectors of dimension 128)
        dummy_embeddings = np.random.rand(2, 128).astype(np.float32)
        np.save(npy_path, dummy_embeddings)

        # Test build()
        builder = FAISSBuilder(persist_dir=persist_dir)
        index, meta = builder.build(embeddings_path=npy_path, metadata_path=json_path)

        assert index.ntotal == 2
        assert len(meta) == 2
        assert (persist_dir / "index.faiss").exists()
        assert (persist_dir / "metadata.pkl").exists()

        # Test load()
        new_builder = FAISSBuilder(persist_dir=persist_dir)
        loaded_index, loaded_meta = new_builder.load()
        assert loaded_index.ntotal == 2
        assert len(loaded_meta) == 2

        # Test search()
        query_vec = dummy_embeddings[0]
        results = new_builder.search(query_vec, top_k=1)
        assert len(results) == 1
        assert results[0]["metadata"]["id"] == "chunk_01"
        assert results[0]["score"] > 0.99  # Cosine similarity self-match

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
