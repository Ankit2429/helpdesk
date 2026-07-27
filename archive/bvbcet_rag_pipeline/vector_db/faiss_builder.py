"""Production-grade FAISS Vector Database Builder and Search Engine.

Builds an L2-normalized IndexFlatIP (Cosine Similarity) FAISS vector store
from pre-computed embeddings and metadata JSON records.

Persist Directory:
    vector_db/faiss/

Persist Files:
    index.faiss
    metadata.pkl
"""

import argparse
import json
import logging
from pathlib import Path
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np

from logger.logger import get_logger

logger = get_logger("faiss_builder")

DEFAULT_PERSIST_DIR: Path = Path("vector_db/faiss")


class FAISSBuilder:
    """Manages FAISS IndexFlatIP creation, persistence, loading, and Cosine Similarity search."""

    def __init__(self, persist_dir: Path = DEFAULT_PERSIST_DIR) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.persist_dir / "index.faiss"
        self.metadata_file = self.persist_dir / "metadata.pkl"

        self.index: Optional[faiss.IndexFlatIP] = None
        self.metadata: List[Dict[str, Any]] = []

    def build(
        self,
        embeddings_path: Path = Path("embeddings/embeddings.npy"),
        metadata_path: Path = Path("embeddings/metadata.json"),
    ) -> Tuple[faiss.IndexFlatIP, List[Dict[str, Any]]]:
        """Build FAISS IndexFlatIP from embeddings array, normalize vectors, and persist to disk."""
        start_time = time.time()
        logger.info(f"Loading embeddings array: {embeddings_path}")
        logger.info(f"Loading metadata records: {metadata_path}")

        if not embeddings_path.exists():
            raise FileNotFoundError(f"Embeddings file missing: {embeddings_path}")

        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file missing: {metadata_path}")

        # Load input files
        embeddings = np.load(embeddings_path).astype(np.float32)
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata_records = json.load(f)

        if embeddings.shape[0] != len(metadata_records):
            logger.warning(
                f"Count mismatch between embeddings rows ({embeddings.shape[0]}) and metadata records ({len(metadata_records)})"
            )
            min_len = min(embeddings.shape[0], len(metadata_records))
            embeddings = embeddings[:min_len]
            metadata_records = metadata_records[:min_len]

        num_vectors, dimension = embeddings.shape
        logger.info(f"Building FAISS IndexFlatIP for {num_vectors} vectors of dimension {dimension}...")

        # Normalize L2 vectors for Cosine Similarity via Inner Product (IndexFlatIP)
        faiss.normalize_L2(embeddings)

        # Create FAISS IndexFlatIP index
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.metadata = metadata_records

        # Save index.faiss and metadata.pkl
        faiss.write_index(self.index, str(self.index_file.resolve()))
        with open(self.metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

        elapsed = round(time.time() - start_time, 2)
        index_size_mb = round(self.get_persist_size_mb(), 2)

        self.print_verification(
            embedding_count=self.index.ntotal,
            index_dimension=dimension,
            index_size_mb=index_size_mb,
            elapsed_seconds=elapsed,
        )

        return self.index, self.metadata

    def load(self) -> Tuple[faiss.IndexFlatIP, List[Dict[str, Any]]]:
        """Load existing index.faiss and metadata.pkl from disk."""
        if not self.index_file.exists() or not self.metadata_file.exists():
            raise FileNotFoundError(
                f"FAISS index or metadata missing in '{self.persist_dir}'. Expected index.faiss and metadata.pkl"
            )

        logger.info(f"Loading FAISS index from {self.index_file}")
        self.index = faiss.read_index(str(self.index_file.resolve()))

        logger.info(f"Loading metadata from {self.metadata_file}")
        with open(self.metadata_file, "rb") as f:
            self.metadata = pickle.load(f)

        logger.info(f"Successfully loaded FAISS index. Total vectors: {self.index.ntotal}, Dimension: {self.index.d}")
        return self.index, self.metadata

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Perform Cosine Similarity search using normalized query vector."""
        if self.index is None or not self.metadata:
            self.load()

        if self.index is None:
            raise RuntimeError("FAISS index is not initialized or loaded.")

        # Ensure query vector is float32 2D array
        query_vec = np.asarray(query_vector, dtype=np.float32)
        if query_vec.ndim == 1:
            query_vec = np.expand_dims(query_vec, axis=0)

        # Normalize L2 query vector
        faiss.normalize_L2(query_vec)

        # Perform FAISS search
        top_k = min(top_k, self.index.ntotal)
        distances, indices = self.index.search(query_vec, top_k)

        results: List[Dict[str, Any]] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append(
                {
                    "score": float(score),
                    "index": int(idx),
                    "metadata": meta,
                }
            )

        return results

    def get_persist_size_mb(self) -> float:
        """Calculate combined on-disk size of index.faiss and metadata.pkl in Megabytes."""
        total_bytes = 0
        for p in [self.index_file, self.metadata_file]:
            if p.exists():
                total_bytes += p.stat().st_size
        return total_bytes / (1024 * 1024)

    @staticmethod
    def print_verification(
        embedding_count: int,
        index_dimension: int,
        index_size_mb: float,
        elapsed_seconds: float,
    ) -> None:
        """Print clean human-readable verification summary."""
        print("\n" + "=" * 50)
        print("FAISS VECTOR STORE SUMMARY")
        print("=" * 50)
        print(f"Embedding Count : {embedding_count}")
        print(f"Index Dimension : {index_dimension}")
        print(f"Index Size      : {index_size_mb} MB")
        print(f"Build Time      : {elapsed_seconds}s")
        print("=" * 50 + "\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for FAISS builder."""
    parser = argparse.ArgumentParser(description="FAISS Vector Store Builder CLI")
    parser.add_argument("-e", "--embeddings", type=Path, default=Path("embeddings/embeddings.npy"), help="Input embeddings.npy path")
    parser.add_argument("-m", "--metadata", type=Path, default=Path("embeddings/metadata.json"), help="Input metadata.json path")
    parser.add_argument("-p", "--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR, help="Output directory for index.faiss and metadata.pkl")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python -m vector_db.faiss_builder."""
    args = parse_args()
    builder = FAISSBuilder(persist_dir=args.persist_dir)
    builder.build(
        embeddings_path=args.embeddings,
        metadata_path=args.metadata,
    )


if __name__ == "__main__":
    main()
