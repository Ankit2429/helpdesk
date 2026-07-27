"""Production-grade Chunk Metadata Processor and Storage Layer.

Processes Chunk objects from semantic_chunker, extracts rich metadata,
performs SHA256 content deduplication, and generates chunks.jsonl,
duplicate_chunks.json, and statistics.json.
"""

from dataclasses import asdict, dataclass
import datetime
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

from chunker.semantic_chunker import Chunk

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Metadata attributes for an individual text chunk."""

    id: str
    title: str
    heading: str
    heading_level: int
    relative_file_path: str
    source_filename: str
    category: str
    url: str
    chunk_index: int
    timestamp: str
    sha256_hash: str
    word_count: int
    token_count: int


@dataclass
class ChunkRecord:
    """JSONL output record containing text and metadata."""

    text: str
    metadata: ChunkMetadata


@dataclass
class ChunkStatistics:
    """Execution metrics for chunk processing and storage."""

    markdown_files_processed: int
    chunks_created: int
    duplicates_removed: int
    average_chunk_size: float
    largest_chunk: int
    smallest_chunk: int


class ChunkMetadataProcessor:
    """Processes Chunk objects, performs SHA256 deduplication, and writes chunks JSONL storage."""

    def __init__(self, output_dir: Path = Path("chunks")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.output_dir / "chunks.jsonl"
        self.duplicates_path = self.output_dir / "duplicate_chunks.json"
        self.statistics_path = self.output_dir / "statistics.json"

    @staticmethod
    def compute_sha256(text: str) -> str:
        """Compute SHA256 hex digest of chunk text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_url_from_text(text: str) -> str:
        """Extract Source URL from Markdown header line if present."""
        match = re.search(r"\*\*Source URL:\*\*\s*(https?://[^\s]+)", text)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def infer_category_from_path(file_path_str: str) -> str:
        """Infer target category folder from relative file path."""
        parts = Path(file_path_str).parts
        if len(parts) > 1:
            return parts[-2]
        return "miscellaneous"

    def process_chunks(
        self,
        chunks: List[Chunk],
        markdown_files_processed: int = 0,
        base_markdown_dir: Optional[Path] = None,
    ) -> List[ChunkRecord]:
        """Process list of Chunk objects, deduplicate using SHA256, and write outputs."""
        seen_sha256: Set[str] = set()
        unique_records: List[ChunkRecord] = []
        duplicate_records: List[Dict[str, Any]] = []

        now_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        chunks_created_count = 0
        duplicates_removed_count = 0

        token_sizes: List[int] = []

        for idx, chunk in enumerate(chunks):
            try:
                chunk_text = chunk.text
                if not chunk_text or not chunk_text.strip():
                    continue

                sha256_hash = self.compute_sha256(chunk_text)

                if sha256_hash in seen_sha256:
                    duplicates_removed_count += 1
                    duplicate_records.append(
                        {
                            "chunk_id": chunk.id,
                            "title": chunk.title,
                            "sha256_hash": sha256_hash,
                            "token_count": chunk.token_count,
                        }
                    )
                    continue

                seen_sha256.add(sha256_hash)

                # Extract metadata details
                url = self.extract_url_from_text(chunk_text)
                word_count = len(chunk_text.split())

                # Generate relative path and category
                source_filename = f"{chunk.id.split('_')[0]}.md"
                relative_path = f"markdown/{source_filename}"
                category = self.infer_category_from_path(relative_path)

                meta = ChunkMetadata(
                    id=chunk.id,
                    title=chunk.title,
                    heading=chunk.heading,
                    heading_level=chunk.level,
                    relative_file_path=relative_path,
                    source_filename=source_filename,
                    category=category,
                    url=url,
                    chunk_index=idx,
                    timestamp=now_timestamp,
                    sha256_hash=sha256_hash,
                    word_count=word_count,
                    token_count=chunk.token_count,
                )

                record = ChunkRecord(text=chunk_text, metadata=meta)
                unique_records.append(record)
                chunks_created_count += 1
                token_sizes.append(chunk.token_count)

            except Exception as err:
                logger.error(f"Error processing chunk {chunk.id}: {err}")
                continue

        # Write chunks.jsonl
        try:
            with open(self.jsonl_path, "w", encoding="utf-8") as f:
                for rec in unique_records:
                    row = {
                        "text": rec.text,
                        "metadata": asdict(rec.metadata),
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            logger.info(f"Wrote {len(unique_records)} chunks to {self.jsonl_path}")
        except Exception as err:
            logger.error(f"Failed writing chunks.jsonl: {err}")

        # Write duplicate_chunks.json
        try:
            with open(self.duplicates_path, "w", encoding="utf-8") as f:
                json.dump(duplicate_records, f, indent=2)
            logger.info(f"Wrote {len(duplicate_records)} duplicate records to {self.duplicates_path}")
        except Exception as err:
            logger.error(f"Failed writing duplicate_chunks.json: {err}")

        # Compute statistics metrics
        avg_size = float(sum(token_sizes) / len(token_sizes)) if token_sizes else 0.0
        largest = max(token_sizes) if token_sizes else 0
        smallest = min(token_sizes) if token_sizes else 0

        stats = ChunkStatistics(
            markdown_files_processed=markdown_files_processed,
            chunks_created=chunks_created_count,
            duplicates_removed=duplicates_removed_count,
            average_chunk_size=round(avg_size, 2),
            largest_chunk=largest,
            smallest_chunk=smallest,
        )

        # Write statistics.json
        try:
            with open(self.statistics_path, "w", encoding="utf-8") as f:
                json.dump(asdict(stats), f, indent=2)
            logger.info(f"Wrote statistics metrics to {self.statistics_path}")
        except Exception as err:
            logger.error(f"Failed writing statistics.json: {err}")

        return unique_records
