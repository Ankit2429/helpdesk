"""Unit tests for SHA256 embedding disk cache."""

from pathlib import Path
import shutil
import tempfile
import numpy as np

from embeddings.embedding_generator import EmbeddingGenerator


def test_embedding_generator_cache():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            batch_size=16,
            output_dir=temp_dir,
            enable_cache=True,
        )

        sample_text = "The Computer Science Department offers B.E. in Artificial Intelligence."
        text_hash = generator.get_text_hash(sample_text)

        # Initial check should be cache miss
        assert generator.get_cached_vector(text_hash) is None

        # Save dummy vector to cache
        dummy_vec = np.ones((384,), dtype=np.float32)
        generator.save_cached_vector(text_hash, dummy_vec)

        # Subsequent check should be cache hit
        cached_vec = generator.get_cached_vector(text_hash)
        assert cached_vec is not None
        assert cached_vec.shape == (384,)
        assert np.array_equal(cached_vec, dummy_vec)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
