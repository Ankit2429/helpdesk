"""Cross-Encoder Re-Ranking Engine.

Re-ranks top candidate chunks using local Cross-Encoder models
(cross-encoder/ms-marco-MiniLM-L-6-v2), applying dynamic similarity thresholding.
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple

import torch
from sentence_transformers import CrossEncoder

from logger.logger import get_logger

logger = get_logger("reranker")


@dataclass
class RerankedCandidate:
    """Dataclass holding candidate chunk and cross-encoder re-rank score."""

    text: str
    metadata: Dict[str, Any]
    rerank_score: float
    original_rank: int


class CrossEncoderReranker:
    """Cross-Encoder Re-Ranking Engine."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        score_threshold: float = 0.35,
    ) -> None:
        self.model_name = model_name
        self.score_threshold = score_threshold
        device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(f"Loading Cross-Encoder re-ranker '{self.model_name}' on device '{device}'")
        try:
            self.model = CrossEncoder(self.model_name, device=device)
        except Exception as err:
            logger.warning(f"Failed loading CrossEncoder model '{self.model_name}': {err}. Using fallback re-scoring.")
            self.model = None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[RerankedCandidate]:
        """Re-rank candidate list using Cross-Encoder model and filter by threshold."""
        if not candidates:
            return []

        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold
        pairs = [(query, cand.get("text", "")) for cand in candidates]

        reranked: List[RerankedCandidate] = []

        if self.model is not None:
            try:
                raw_scores = self.model.predict(pairs, show_progress_bar=False)
                # Convert logits to 0-1 sigmoid probability score
                sigmoid_scores = [float(1.0 / (1.0 + torch.exp(-torch.tensor(s)).item())) for s in raw_scores]

                for idx, (cand, score) in enumerate(zip(candidates, sigmoid_scores), start=1):
                    reranked.append(
                        RerankedCandidate(
                            text=cand.get("text", ""),
                            metadata=cand.get("metadata", {}),
                            rerank_score=round(score, 4),
                            original_rank=idx,
                        )
                    )
            except Exception as err:
                logger.error(f"Error during Cross-Encoder prediction: {err}")
                self.model = None

        if self.model is None:
            # Fallback to vector similarity score in metadata
            for idx, cand in enumerate(candidates, start=1):
                fallback_score = cand.get("score", cand.get("dense_score", 0.50))
                reranked.append(
                    RerankedCandidate(
                        text=cand.get("text", ""),
                        metadata=cand.get("metadata", {}),
                        rerank_score=round(float(fallback_score), 4),
                        original_rank=idx,
                    )
                )

        # Sort descending by re-rank score
        reranked.sort(key=lambda x: x.rerank_score, reverse=True)

        # Filter by threshold (fallback to top_k if threshold eliminates all candidates)
        filtered_candidates = [c for c in reranked if c.rerank_score >= effective_threshold]
        final_selected = filtered_candidates[:top_k] if filtered_candidates else reranked[:top_k]

        logger.info(
            f"Re-ranked {len(candidates)} candidates -> {len(final_selected)} selected (Top score: {final_selected[0].rerank_score if final_selected else 0.0:.4f})"
        )
        return final_selected
