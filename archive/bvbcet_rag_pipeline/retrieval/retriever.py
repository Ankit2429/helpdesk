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

from config.config import CHROMA_DIR, DEFAULT_COLLECTION_NAME
from embeddings.embedding_generator import DEFAULT_MODEL
from logger.logger import get_logger

logger = get_logger("retriever")

DEFAULT_PERSIST_DIR: Path = CHROMA_DIR


from retrieval.citation_formatter import CitationFormatter, FormattedCitationOutput
from retrieval.reranker import CrossEncoderReranker
from utils.multilingual_utils import detect_language, normalize_text, select_model_for_language
from vector_db.hybrid_search import HybridSearchEngine


class ChromaRetriever:
    """Offline RAG Retriever querying ChromaDB vector store and returning LangChain Documents."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        persist_dir: Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        top_k: int = 5,
        score_threshold: float = 0.35,
        enable_reranker: bool = True,
        enable_hybrid: bool = True,
    ) -> None:
        self.model_name = model_name
        self.persist_dir = Path(persist_dir).resolve()
        self.collection_name = collection_name
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.enable_reranker = enable_reranker
        self.enable_hybrid = enable_hybrid

        # Device detection
        self.gpu_available = torch.cuda.is_available()
        self.device = "cuda" if self.gpu_available else "cpu"

        logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'")
        self.model = SentenceTransformer(self.model_name, device=self.device)

        logger.info(f"Connecting to persistent ChromaDB client at '{self.persist_dir}'")
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))

        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        vector_count = self.collection.count()
        if vector_count == 0:
            logger.warning(
                f"Connected to collection '{self.collection_name}' at '{self.persist_dir}', but it contains 0 vectors! "
                f"Please populate vectors using 'python -m vector_db.chroma_builder'."
            )
        else:
            logger.info(f"Connected to collection '{self.collection_name}'. Total vectors: {vector_count}")

        # Subsystems
        self.reranker = CrossEncoderReranker(score_threshold=score_threshold) if enable_reranker else None
        self.hybrid_engine = HybridSearchEngine(rrf_k=60) if enable_hybrid else None

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

        # Step 1: Multilingual Detection & Text Normalization
        lang_code, _ = detect_language(question)
        normalized_query = normalize_text(question)

        logger.info(f"Processing query: '{normalized_query}' [Lang: {lang_code}] (top_k={effective_top_k}, threshold={effective_threshold})")

        # Step 2: Embed question
        query_vector = self.embed_question(normalized_query)

        # Step 3: Build metadata filter
        where_clause = self.build_where_clause(
            category=category,
            department=department,
            metadata_filter=metadata_filter,
        )

        # Step 4: Dense Similarity search in ChromaDB
        candidate_k = min(effective_top_k * 4 if rerank else effective_top_k, max(1, self.collection.count()))
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=candidate_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as err:
            logger.error(f"ChromaDB query error: {err}")
            return []

        raw_candidates: List[Dict[str, Any]] = []
        if results and results.get("documents") and results["documents"][0]:
            raw_docs = results["documents"][0]
            raw_metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(raw_docs)
            raw_dists = results["distances"][0] if results.get("distances") else [1.0] * len(raw_docs)

            for doc_text, meta, dist in zip(raw_docs, raw_metas, raw_dists):
                score = round(max(0.0, 1.0 - float(dist)), 4)
                raw_candidates.append({"text": doc_text, "metadata": dict(meta or {}), "score": score})

        if not raw_candidates:
            logger.info("No matching chunks found in ChromaDB collection.")
            return []

        # Step 5: Optional Cross-Encoder Re-Ranking Stage
        if rerank and self.reranker is not None:
            reranked = self.reranker.rerank(
                query=normalized_query,
                candidates=raw_candidates,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )
            selected_items = [
                {
                    "text": r.text,
                    "metadata": {**r.metadata, "score": r.rerank_score},
                    "score": r.rerank_score,
                }
                for r in reranked
            ]
        else:
            filtered = [c for c in raw_candidates if c["score"] >= effective_threshold]
            filtered.sort(key=lambda c: c["score"], reverse=True)
            selected_items = filtered[:effective_top_k]

        # Step 6: Convert to LangChain Documents
        documents: List[Document] = []
        for item in selected_items:
            doc_metadata = dict(item.get("metadata", {}))
            doc_metadata["score"] = item.get("score", 0.0)
            doc_metadata["chunk_id"] = doc_metadata.get("chunk_id") or doc_metadata.get("id", "")
            doc_metadata["source"] = doc_metadata.get("source") or doc_metadata.get("source_filename") or doc_metadata.get("source_doc", "")
            doc_metadata["heading"] = doc_metadata.get("heading", "")
            doc_metadata["relative_path"] = doc_metadata.get("relative_path") or doc_metadata.get("relative_file_path", "")
            doc_metadata["category"] = doc_metadata.get("category", "")
            doc_metadata["language"] = lang_code

            documents.append(
                Document(
                    page_content=item.get("text", ""),
                    metadata=doc_metadata,
                )
            )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Retrieved {len(documents)} chunks in {elapsed_ms} ms")
        self.display_search_results(question, documents, elapsed_ms)

        return documents

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
    parser.add_argument("-m", "--model", type=str, default="all-MiniLM-L6-v2", help="Embedding model name")
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
