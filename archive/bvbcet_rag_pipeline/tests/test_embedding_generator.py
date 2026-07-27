"""Unit tests for EmbeddingGenerator."""

import json
from pathlib import Path
import shutil
import tempfile
import numpy as np

from embeddings.embedding_generator import EmbeddingGenerator


def test_embedding_generator_workflow():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        jsonl_path = temp_dir / "chunks.jsonl"
        output_dir = temp_dir / "embeddings_out"

        # Create dummy chunk records
        records = [
            {"text": "Sample text for chunk one", "metadata": {"id": "chunk_1", "title": "Doc 1"}},
            {"text": "Sample text for chunk two", "metadata": {"id": "chunk_2", "title": "Doc 2"}},
        ]

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        # Initialize generator with small model for speed
        generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            batch_size=2,
            output_dir=output_dir,
        )

        embeddings, metadata = generator.generate(jsonl_path=jsonl_path)

        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape[0] == 2
        assert embeddings.shape[1] == 384  # MiniLM dimension
        assert len(metadata) == 2

        # Verify persisted files
        assert (output_dir / "embeddings.npy").exists()
        assert (output_dir / "metadata.json").exists()
        assert (output_dir / "embedding_statistics.json").exists()

        with open(output_dir / "embedding_statistics.json", "r", encoding="utf-8") as f:
            stats = json.load(f)
            assert stats["total_chunks"] == 2
            assert stats["embedding_dimension"] == 384
            assert stats["model_used"] == "all-MiniLM-L6-v2"

        # Resume test: call generate again on the same file -> should skip processing
        embeddings_resume, metadata_resume = generator.generate(jsonl_path=jsonl_path)
        assert embeddings_resume.shape[0] == 2

    finally:
        shutil.rmtree(temp_dir)
