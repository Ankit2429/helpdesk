"""Production-grade ChromaDB Vector Database Builder.

Builds and updates a persistent ChromaDB vector store from pre-computed embeddings
and chunk JSONL records. Supports incremental indexing, upserts, resume capability,
and metadata indexing.

Persist Directory:
    vector_db/chroma/

Collection Name:
    bvbcet_knowledge
"""

import argparse
import json
import logging
from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
import numpy as np
from tqdm import tqdm

from logger.logger import get_logger

logger = get_logger("chroma_builder")

DEFAULT_COLLECTION_NAME: str = "bvbcet_knowledge"
DEFAULT_PERSIST_DIR: Path = Path("vector_db/chroma")


class ChromaBuilder:
    """Manages persistent ChromaDB vector store creation, incremental upserts, and querying."""

    def __init__(
        self,
        persist_dir: Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        batch_size: int = 100,
    ) -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing Persistent ChromaDB Client at '{self.persist_dir}'")
        self.client = chromadb.PersistentClient(path=str(self.persist_dir.resolve()))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Connected to collection '{self.collection_name}'. Current count: {self.collection.count()}")

    @staticmethod
    def sanitize_metadata(metadata_dict: Dict[str, Any]) -> Dict[str, str | int | float | bool]:
        """Sanitize metadata dict for ChromaDB compatibility (primitives only)."""
        clean_meta: Dict[str, str | int | float | bool] = {}
        for key, val in metadata_dict.items():
            if val is None:
                clean_meta[key] = ""
            elif isinstance(val, (str, int, float, bool)):
                clean_meta[key] = val
            elif isinstance(val, (list, dict)):
                clean_meta[key] = json.dumps(val)
            else:
                clean_meta[key] = str(val)

        # Standardized key aliases for seamless RAG search
        if "category" in clean_meta:
            clean_meta["category"] = clean_meta["category"]
        if "heading" in clean_meta:
            clean_meta["heading"] = clean_meta["heading"]
        if "source_filename" in clean_meta:
            clean_meta["source"] = clean_meta["source_filename"]
        if "relative_file_path" in clean_meta:
            clean_meta["relative_path"] = clean_meta["relative_file_path"]
        if "id" in clean_meta:
            clean_meta["chunk_id"] = clean_meta["id"]

        return clean_meta

    def build_index(
        self,
        jsonl_path: Path = Path("chunks/chunks.jsonl"),
        embeddings_path: Path = Path("embeddings/embeddings.npy"),
        delete_stale: bool = True,
    ) -> int:
        """Build/update ChromaDB collection using pre-computed embeddings and JSONL records."""
        start_time = time.time()
        logger.info(f"Loading input JSONL: {jsonl_path}")
        logger.info(f"Loading input Embeddings: {embeddings_path}")

        if not jsonl_path.exists():
            logger.error(f"JSONL input file missing: {jsonl_path}")
            return 0

        if not embeddings_path.exists():
            logger.error(f"Embeddings array missing: {embeddings_path}")
            return 0

        # Load chunk records
        records: List[Dict[str, Any]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue

        # Load embedding matrix
        embeddings_matrix = np.load(embeddings_path)

        if len(records) != embeddings_matrix.shape[0]:
            logger.error(
                f"Mismatch between records count ({len(records)}) and embeddings rows ({embeddings_matrix.shape[0]})"
            )
            min_len = min(len(records), embeddings_matrix.shape[0])
            records = records[:min_len]
            embeddings_matrix = embeddings_matrix[:min_len]

        total_chunks = len(records)
        input_ids = {str(rec.get("metadata", {}).get("id", f"chunk_{idx}")) for idx, rec in enumerate(records)}

        # Delete stale vectors if enabled
        if delete_stale:
            try:
                existing_data = self.collection.get(include=[])
                existing_ids = set(existing_data.get("ids", []))
                stale_ids = list(existing_ids - input_ids)
                if stale_ids:
                    logger.info(f"Deleting {len(stale_ids)} stale vectors from ChromaDB collection...")
                    self.collection.delete(ids=stale_ids)
            except Exception as err:
                logger.warning(f"Error checking/deleting stale vectors: {err}")

        logger.info(f"Upserting {total_chunks} vector records into ChromaDB...")

        # Batch upsert into ChromaDB
        for i in tqdm(range(0, total_chunks, self.batch_size), desc="Indexing Vectors", unit="batch"):
            batch_records = records[i : i + self.batch_size]
            batch_vecs = embeddings_matrix[i : i + self.batch_size].tolist()

            batch_ids: List[str] = []
            batch_docs: List[str] = []
            batch_metas: List[Dict[str, Any]] = []

            for idx, rec in enumerate(batch_records):
                meta = rec.get("metadata", {})
                chunk_id = meta.get("id", f"chunk_{i + idx}")
                doc_text = rec.get("text", "")

                clean_meta = self.sanitize_metadata(meta)

                batch_ids.append(str(chunk_id))
                batch_docs.append(doc_text)
                batch_metas.append(clean_meta)

            try:
                self.collection.upsert(
                    ids=batch_ids,
                    embeddings=batch_vecs,
                    documents=batch_docs,
                    metadatas=batch_metas,
                )
            except Exception as err:
                logger.error(f"Error upserting batch starting at {i}: {err}")
                continue

        final_count = self.collection.count()
        elapsed = round(time.time() - start_time, 2)
        dir_size_mb = round(self.get_directory_size_mb(self.persist_dir), 2)

        self.print_verification(
            vectors_stored=final_count,
            collection_name=self.collection_name,
            db_size_mb=dir_size_mb,
            elapsed_seconds=elapsed,
        )

        return final_count

    @staticmethod
    def get_directory_size_mb(directory: Path) -> float:
        """Calculate total directory size in Megabytes."""
        total_bytes = 0
        if directory.exists():
            for p in directory.rglob("*"):
                if p.is_file():
                    total_bytes += p.stat().st_size
        return total_bytes / (1024 * 1024)

    @staticmethod
    def print_verification(
        vectors_stored: int,
        collection_name: str,
        db_size_mb: float,
        elapsed_seconds: float,
    ) -> None:
        """Print clean human-readable verification summary."""
        print("\n" + "=" * 50)
        print("CHROMADB VECTOR STORE SUMMARY")
        print("=" * 50)
        print(f"Collection Name  : {collection_name}")
        print(f"Vectors Stored   : {vectors_stored}")
        print(f"Database Size    : {db_size_mb} MB")
        print(f"Indexing Time    : {elapsed_seconds}s")
        print("=" * 50 + "\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for ChromaDB builder."""
    parser = argparse.ArgumentParser(description="ChromaDB Vector Store Builder CLI")
    parser.add_argument("-i", "--input-jsonl", type=Path, default=Path("chunks/chunks.jsonl"), help="Input chunks.jsonl path")
    parser.add_argument("-e", "--embeddings", type=Path, default=Path("embeddings/embeddings.npy"), help="Input embeddings.npy path")
    parser.add_argument("-p", "--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR, help="ChromaDB persist directory")
    parser.add_argument("-c", "--collection", type=str, default=DEFAULT_COLLECTION_NAME, help="Collection name")
    parser.add_argument("-b", "--batch-size", type=int, default=100, help="Batch size for upserting")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python -m vector_db.chroma_builder."""
    args = parse_args()
    builder = ChromaBuilder(
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        batch_size=args.batch_size,
    )
    builder.build_index(
        jsonl_path=args.input_jsonl,
        embeddings_path=args.embeddings,
    )


if __name__ == "__main__":
    main()
