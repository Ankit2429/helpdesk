"""Production-grade Offline Embedding Generator.

Generates dense vector embeddings for text chunks using local HuggingFace / SentenceTransformer models.
Supports GPU acceleration with CPU fallback, batch processing, resume/incremental updates,
and metadata preservation.

Outputs:
    - embeddings.npy
    - metadata.json
    - embedding_statistics.json
"""

import argparse
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from logger.logger import get_logger

logger = get_logger("embedding_generator")

DEFAULT_MODEL: str = "BAAI/bge-base-en-v1.5"
SUPPORTED_MODELS: List[str] = [
    "BAAI/bge-base-en-v1.5",
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-large-en-v1.5",
    "all-MiniLM-L6-v2",
]


@dataclass
class EmbeddingStatistics:
    """Statistics and metrics for embedding generation."""

    total_chunks: int
    embedding_dimension: int
    model_used: str
    execution_time: float
    gpu_used: bool
    average_embedding_time: float


class EmbeddingGenerator:
    """Generates offline dense vector embeddings for JSONL chunk records."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = 32,
        output_dir: Path = Path("embeddings"),
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.embeddings_path = self.output_dir / "embeddings.npy"
        self.metadata_path = self.output_dir / "metadata.json"
        self.stats_path = self.output_dir / "embedding_statistics.json"

        # Hardware acceleration detection
        self.gpu_available = torch.cuda.is_available()
        self.device = "cuda" if self.gpu_available else "cpu"
        logger.info(f"Initializing embedding model '{self.model_name}' on device '{self.device}'")

        try:
            self.model = SentenceTransformer(self.model_name, device=self.device)
        except Exception as err:
            logger.error(f"Failed loading model '{self.model_name}': {err}")
            raise

    def load_input_chunks(self, jsonl_path: Path) -> List[Dict[str, Any]]:
        """Load text and metadata records from chunks.jsonl file."""
        records: List[Dict[str, Any]] = []
        if not jsonl_path.exists():
            logger.error(f"Input JSONL file not found: {jsonl_path}")
            return records

        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        record = json.loads(line_str)
                        if "text" in record and "metadata" in record:
                            records.append(record)
                    except json.JSONDecodeError as je:
                        logger.warning(f"Skipping malformed JSON line {line_no} in {jsonl_path}: {je}")
        except Exception as err:
            logger.error(f"Failed reading input file {jsonl_path}: {err}")

        return records

    def load_existing_outputs(self) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]]]:
        """Load existing embeddings.npy and metadata.json for resume support."""
        existing_embeddings: Optional[np.ndarray] = None
        existing_metadata: List[Dict[str, Any]] = []

        if self.embeddings_path.exists() and self.metadata_path.exists():
            try:
                existing_embeddings = np.load(self.embeddings_path)
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    existing_metadata = json.load(f)
                logger.info(
                    f"Found existing embeddings storage with {len(existing_metadata)} records. Resume enabled."
                )
            except Exception as err:
                logger.warning(f"Failed reading existing embeddings/metadata for resume: {err}")
                existing_embeddings = None
                existing_metadata = []

        return existing_embeddings, existing_metadata

    def generate(self, jsonl_path: Path = Path("chunks/chunks.jsonl")) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Generate dense vector embeddings for chunks with batching and resume support."""
        start_time = time.time()
        input_records = self.load_input_chunks(jsonl_path)
        total_input_chunks = len(input_records)

        if total_input_chunks == 0:
            logger.warning(f"No valid records found in {jsonl_path}")
            empty_arr = np.empty((0, 0), dtype=np.float32)
            return empty_arr, []

        existing_embeddings, existing_metadata = self.load_existing_outputs()
        seen_ids = {meta.get("id") for meta in existing_metadata if meta.get("id")}

        # Filter out chunks already embedded
        new_records = [rec for rec in input_records if rec["metadata"].get("id") not in seen_ids]

        if not new_records and existing_embeddings is not None:
            logger.info("All chunks are already embedded. Skipping generation.")
            return existing_embeddings, existing_metadata

        logger.info(f"Generating embeddings for {len(new_records)} new chunk(s) (Total: {total_input_chunks}).")

        new_texts = [rec["text"] for rec in new_records]
        new_meta = [rec["metadata"] for rec in new_records]

        # Batch vector encoding
        new_embeddings_list: List[np.ndarray] = []
        encode_start = time.time()

        for i in tqdm(range(0, len(new_texts), self.batch_size), desc="Embedding Chunks", unit="batch"):
            batch_texts = new_texts[i : i + self.batch_size]
            try:
                batch_vecs = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                new_embeddings_list.append(batch_vecs.astype(np.float32))
            except Exception as err:
                logger.error(f"Error encoding batch starting at index {i}: {err}")
                continue

        if new_embeddings_list:
            new_embeddings_arr = np.vstack(new_embeddings_list)
        else:
            new_embeddings_arr = np.empty((0, 0), dtype=np.float32)

        # Merge with existing outputs if resuming
        if existing_embeddings is not None and existing_embeddings.size > 0:
            final_embeddings = np.vstack([existing_embeddings, new_embeddings_arr])
            final_metadata = existing_metadata + new_meta
        else:
            final_embeddings = new_embeddings_arr
            final_metadata = new_meta

        elapsed_time = round(time.time() - start_time, 2)
        total_chunks_processed = len(final_metadata)
        dim = final_embeddings.shape[1] if final_embeddings.size > 0 else 0
        avg_time = round(elapsed_time / total_chunks_processed, 4) if total_chunks_processed > 0 else 0.0

        # Persist outputs to disk
        try:
            np.save(self.embeddings_path, final_embeddings)
            logger.info(f"Saved embeddings array of shape {final_embeddings.shape} to {self.embeddings_path}")

            with open(self.metadata_path, "w", encoding="utf-8") as f:
                json.dump(final_metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved metadata records to {self.metadata_path}")

            stats = EmbeddingStatistics(
                total_chunks=total_chunks_processed,
                embedding_dimension=dim,
                model_used=self.model_name,
                execution_time=elapsed_time,
                gpu_used=self.gpu_available,
                average_embedding_time=avg_time,
            )

            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump(asdict(stats), f, indent=2)
            logger.info(f"Saved embedding statistics to {self.stats_path}")

        except Exception as err:
            logger.error(f"Failed persisting embedding output files: {err}")

        return final_embeddings, final_metadata


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for embedding generator."""
    parser = argparse.ArgumentParser(description="Offline Batch Embedding Generator CLI")
    parser.add_argument("-i", "--input", type=Path, default=Path("chunks/chunks.jsonl"), help="Input chunks.jsonl file path")
    parser.add_argument("-o", "--output", type=Path, default=Path("embeddings"), help="Output directory for embeddings")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, choices=SUPPORTED_MODELS, help="HuggingFace model name")
    parser.add_argument("-b", "--batch-size", type=int, default=32, help="Batch size for vector encoding")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python -m embeddings.embedding_generator."""
    args = parse_args()
    generator = EmbeddingGenerator(
        model_name=args.model,
        batch_size=args.batch_size,
        output_dir=args.output,
    )
    generator.generate(jsonl_path=args.input)


if __name__ == "__main__":
    main()
