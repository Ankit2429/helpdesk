"""Production-grade Offline RAG Retriever Engine.

Embeds user questions using local HuggingFace / SentenceTransformer models,
executes Cosine Similarity search over persistent ChromaDB vector store,
supports metadata/category/department filtering, score thresholding,
optional score re-ranking, and outputs LangChain Document objects.
"""

import argparse
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union

import chromadb
from langchain_core.documents import Document
import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from embeddings.embedding_generator import DEFAULT_MODEL
from logger.logger import get_logger

logger = get_logger("retriever")

DEFAULT_PERSIST_DIR: Path = Path("vector_db/chroma")
DEFAULT_COLLECTION_NAME: str = "bvbcet_knowledge"


class ChromaRetriever:
    """Offline RAG Retriever querying ChromaDB vector store and returning LangChain Documents."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        persist_dir: Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> None:
        self.model_name = model_name
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name
        self.top_k = top_k
        self.score_threshold = score_threshold

        # Device detection
        self.gpu_available = torch.cuda.is_available()
        self.device = "cuda" if self.gpu_available else "cpu"

        logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'")
        self.model = SentenceTransformer(self.model_name, device=self.device)

        logger.info(f"Connecting to persistent ChromaDB client at '{self.persist_dir}'")
        self.client = chromadb.PersistentClient(path=str(self.persist_dir.resolve()))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Connected to collection '{self.collection_name}'. Total vectors: {self.collection.count()}")

    def embed_question(self, question: str) -> List[float]:
        """Embed user query string into normalized float list vector."""
        vec = self.model.encode(
            [question],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vec[0].tolist()

    @staticmethod
    def build_where_clause(
        category: Optional[str] = None,
        department: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Construct ChromaDB metadata filter dictionary."""
        conditions: List[Dict[str, Any]] = []

        if category:
            conditions.append({"category": category})
        if department:
            conditions.append({"department": department})
        if metadata_filter:
            for k, v in metadata_filter.items():
                conditions.append({k: v})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        category: Optional[str] = None,
        department: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
    ) -> List[Document]:
        """Retrieve top matching LangChain Documents for user question."""
        start_time = time.time()
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold

        logger.info(f"Processing query: '{question}' (top_k={effective_top_k}, threshold={effective_threshold})")

        # Step 1: Embed question
        query_vector = self.embed_question(question)

        # Step 2: Build metadata filter
        where_clause = self.build_where_clause(
            category=category,
            department=department,
            metadata_filter=metadata_filter,
        )

        # Step 3: Similarity search in ChromaDB
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=min(effective_top_k * 2 if rerank else effective_top_k, max(1, self.collection.count())),
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as err:
            logger.error(f"ChromaDB query error: {err}")
            return []

        documents: List[Document] = []
        if not results or not results.get("documents") or not results["documents"][0]:
            logger.info("No matching chunks found in ChromaDB collection.")
            return documents

        raw_docs = results["documents"][0]
        raw_metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(raw_docs)
        raw_dists = results["distances"][0] if results.get("distances") else [1.0] * len(raw_docs)

        # Step 4: Convert to LangChain Documents and compute Similarity Scores
        for doc_text, meta, dist in zip(raw_docs, raw_metas, raw_dists):
            # Convert cosine distance to similarity score
            score = round(max(0.0, 1.0 - float(dist)), 4)

            if score < effective_threshold:
                continue

            doc_metadata = dict(meta or {})
            doc_metadata["score"] = score
            doc_metadata["chunk_id"] = doc_metadata.get("chunk_id") or doc_metadata.get("id", "")
            doc_metadata["source"] = doc_metadata.get("source") or doc_metadata.get("source_filename", "")
            doc_metadata["heading"] = doc_metadata.get("heading", "")
            doc_metadata["relative_path"] = doc_metadata.get("relative_path") or doc_metadata.get("relative_file_path", "")
            doc_metadata["category"] = doc_metadata.get("category", "")

            documents.append(
                Document(
                    page_content=doc_text,
                    metadata=doc_metadata,
                )
            )

        # Step 5: Optional Reranking (sort by score descending)
        if rerank:
            documents.sort(key=lambda d: d.metadata.get("score", 0.0), reverse=True)

        final_documents = documents[:effective_top_k]
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        # Log & Display Summary
        logger.info(f"Retrieved {len(final_documents)} chunks in {elapsed_ms} ms")
        self.display_search_results(question, final_documents, elapsed_ms)

        return final_documents

    @staticmethod
    def display_search_results(question: str, documents: List[Document], elapsed_ms: float) -> None:
        """Print clean human-readable search results display."""
        print("\n" + "=" * 60)
        print("CHROMADB RETRIEVAL RESULTS")
        print("=" * 60)
        print(f"User Question : {question}")
        print(f"Chunks Found  : {len(documents)}")
        print(f"Search Time   : {elapsed_ms} ms")
        print("-" * 60)

        for idx, doc in enumerate(documents, start=1):
            meta = doc.metadata
            print(f"Result #{idx} | Similarity Score: {meta.get('score', 0.0):.4f}")
            print(f"  Chunk ID      : {meta.get('chunk_id', 'N/A')}")
            print(f"  Source        : {meta.get('source', 'N/A')}")
            print(f"  Heading       : {meta.get('heading', 'N/A')}")
            print(f"  Relative Path : {meta.get('relative_path', 'N/A')}")
            print(f"  Content Snippet:\n    {doc.page_content[:150].strip()}...")
            print("-" * 60)
        print("=" * 60 + "\n")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for ChromaRetriever query tester."""
    parser = argparse.ArgumentParser(description="ChromaDB RAG Retriever CLI Tester")
    parser.add_argument("-q", "--question", type=str, required=True, help="User question query")
    parser.add_argument("-k", "--top-k", type=int, default=5, help="Top K chunks to retrieve")
    parser.add_argument("-t", "--threshold", type=float, default=0.0, help="Similarity score threshold")
    parser.add_argument("-c", "--category", type=str, default=None, help="Optional category filter")
    parser.add_argument("-d", "--department", type=str, default=None, help="Optional department filter")
    parser.add_argument("-p", "--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR, help="ChromaDB persist directory")
    parser.add_argument("-m", "--model", type=str, default=DEFAULT_MODEL, help="Embedding model name")
    return parser.parse_args()


def main() -> None:
    """CLI Entry point for python -m retrieval.retriever."""
    args = parse_args()
    retriever = ChromaRetriever(
        model_name=args.model,
        persist_dir=args.persist_dir,
        top_k=args.top_k,
        score_threshold=args.threshold,
    )
    retriever.retrieve(
        question=args.question,
        category=args.category,
        department=args.department,
    )


if __name__ == "__main__":
    main()
