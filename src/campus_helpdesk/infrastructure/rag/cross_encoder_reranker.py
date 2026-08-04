"""Cross-Encoder Reranker using local Sentence Transformers for fine-grained query-chunk relevance scoring."""

import logging
import time
from collections.abc import Sequence
from typing import Any

from campus_helpdesk.domain.knowledge import SearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks retrieval candidate chunks using a local Cross-Encoder transformer model."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        enabled: bool = True,
        top_n: int = 10,
        top_m: int = 4,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.enabled = enabled
        self.top_n = top_n
        self.top_m = top_m
        self._model = None
        self._model_loaded = False
        self._load_attempted = False
        self.model_load_time_ms: float = 0.0

        if self.enabled:
            self._lazy_load_model()

    def _lazy_load_model(self) -> None:
        """Attempt loading the Cross-Encoder model with graceful fallback on exception."""
        if self._load_attempted or not self.enabled:
            return

        self._load_attempted = True
        start_time = time.perf_counter()
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading Cross-Encoder reranker model '%s' on %s...", self.model_name, self.device)
            self._model = CrossEncoder(self.model_name, device=self.device, local_files_only=True)
            self._model_loaded = True
            self.model_load_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info("Cross-Encoder model '%s' loaded in %.2fms.", self.model_name, self.model_load_time_ms)
        except Exception as err:
            self._model_loaded = False
            self.model_load_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "Failed to load Cross-Encoder model '%s': %s. Reranker fallback active.",
                self.model_name,
                err,
            )

    def rerank(
        self,
        query: str,
        search_results: Sequence[SearchResult],
        top_m: int | None = None,
    ) -> list[SearchResult]:
        """Rerank candidate SearchResults based on Cross-Encoder query-document relevance scores."""
        reranked_results, _ = self.rerank_with_stats(query, search_results, top_m=top_m)
        return reranked_results

    def rerank_with_stats(
        self,
        query: str,
        search_results: Sequence[SearchResult],
        top_m: int | None = None,
    ) -> tuple[list[SearchResult], dict[str, Any]]:
        """Rerank candidate SearchResults and return diagnostic metrics."""
        start_time = time.perf_counter()
        target_limit = top_m if top_m is not None else self.top_m
        candidates = list(search_results[: self.top_n])
        num_candidates = len(candidates)

        # Fallback path if reranker is disabled or failed to load or no candidates
        if not self.enabled or not self._model_loaded or self._model is None or num_candidates == 0:
            status = "disabled" if not self.enabled else ("fallback" if not self._model_loaded else "empty")
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            stats = {
                "reranker_status": status,
                "model_name": self.model_name,
                "candidates_before": num_candidates,
                "candidates_after": min(num_candidates, target_limit),
                "reranking_latency_ms": duration_ms,
                "model_load_time_ms": self.model_load_time_ms,
            }
            return candidates[:target_limit], stats

        try:
            # Prepare (query, chunk_text) pairs for batch scoring
            pairs = [[query, match.document.content] for match in candidates]
            scores = self._model.predict(pairs)

            # Pair candidates with predicted cross-encoder relevance scores
            scored_candidates = []
            for idx, match in enumerate(candidates):
                score = float(scores[idx])
                # Preserve original search distance in metadata
                if match.document and hasattr(match.document, "metadata"):
                    match.document.metadata["original_distance"] = match.distance
                # Create copy of SearchResult preserving original metadata
                reranked_match = SearchResult(
                    document=match.document,
                    # Higher CrossEncoder score means higher relevance; distance set to -score for sorting compatibility
                    distance=round(-score, 4),
                )
                scored_candidates.append((score, reranked_match))

            # Sort descending by cross-encoder relevance score
            scored_candidates.sort(key=lambda item: item[0], reverse=True)
            top_reranked = [match for _, match in scored_candidates[:target_limit]]

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            stats = {
                "reranker_status": "success",
                "model_name": self.model_name,
                "candidates_before": num_candidates,
                "candidates_after": len(top_reranked),
                "reranking_latency_ms": duration_ms,
                "model_load_time_ms": self.model_load_time_ms,
                "reranked_scores": [
                    {
                        "rank": i + 1,
                        "cross_encoder_score": round(score, 4),
                        "source": match.document.metadata.get("source", "unknown"),
                        "snippet": match.document.content[:100].replace("\n", " "),
                    }
                    for i, (score, match) in enumerate(scored_candidates[:target_limit])
                ],
            }
            return top_reranked, stats

        except Exception as err:
            logger.warning("Error during Cross-Encoder prediction: %s. Using HybridRetriever fallback.", err)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            stats = {
                "reranker_status": "error_fallback",
                "error": str(err),
                "candidates_before": num_candidates,
                "candidates_after": min(num_candidates, target_limit),
                "reranking_latency_ms": duration_ms,
                "model_load_time_ms": self.model_load_time_ms,
            }
            return candidates[:target_limit], stats
