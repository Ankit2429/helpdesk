import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class ChunkStore:
    """Manages the persistence, parsing, and lookup of retrieval chunks from chunks.jsonl."""

    def __init__(self, workspace_root: str = r"d:\helpdesk\anti"):
        self.workspace_root = Path(workspace_root)
        self.chunks_jsonl_path = self.workspace_root / "chunks.jsonl"
        self._chunks_cache = None

    def load_chunks(self, force_reload: bool = False) -> List[Dict]:
        """Load and return all chunks from chunks.jsonl."""
        if self._chunks_cache is not None and not force_reload:
            return self._chunks_cache
            
        if not self.chunks_jsonl_path.exists():
            logger.warning(f"Chunks database '{self.chunks_jsonl_path}' does not exist.")
            return []
            
        chunks = []
        try:
            with open(self.chunks_jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        chunks.append(json.loads(line))
            self._chunks_cache = chunks
            logger.info(f"Loaded {len(chunks)} chunks from store.")
        except Exception as e:
            logger.error(f"Failed to load chunks: {e}")
            return []
            
        return chunks

    def save_chunks(self, chunks: List[Dict]):
        """Persist a list of chunks to chunks.jsonl."""
        try:
            with open(self.chunks_jsonl_path, "w", encoding="utf-8") as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk) + "\n")
            self._chunks_cache = chunks
            logger.info(f"Successfully saved {len(chunks)} chunks to store.")
        except Exception as e:
            logger.error(f"Failed to save chunks: {e}")
            raise IOError(f"Failed to save chunks: {e}")

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Find and return a single chunk by its unique ID."""
        chunks = self.load_chunks()
        for chunk in chunks:
            if chunk.get("id") == chunk_id:
                return chunk
        return None
