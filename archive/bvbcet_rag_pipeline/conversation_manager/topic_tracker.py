"""Production-Grade Campus Topic Tracker Module.

Tracks active campus discussion topics across 10 categories,
computes semantic embedding similarity between conversation turns,
and determines whether to continue topic context or reset context.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from logger.logger import get_logger

logger = get_logger("topic_tracker")

CAMPUS_TOPICS: List[str] = [
    "Departments",
    "Faculty",
    "Buildings",
    "Centers",
    "Labs",
    "Admissions",
    "Placements",
    "Hostels",
    "Courses",
    "Events",
]

TOPIC_DESCRIPTIONS: Dict[str, str] = {
    "Departments": "Academic engineering and science departments, degrees, department head, staff, and curricula.",
    "Faculty": "Professors, teaching faculty members, designation, qualifications, research areas, and contact details.",
    "Buildings": "Campus buildings, blocks, halls, auditoriums, library building, campus map, and infrastructure locations.",
    "Centers": "Research centers, incubation centers, centers of excellence, innovation hubs, and specialized labs.",
    "Labs": "Practical laboratories, computer labs, workshop halls, equipment, and lab facilities.",
    "Admissions": "Admission process, eligibility criteria, KCET, COMEDK, management quota, fee structure, and seat matrix.",
    "Placements": "Career placements, recruiting companies, average salary package, campus drives, and internship opportunities.",
    "Hostels": "Student residential accommodation, hostel fees, mess facilities, room allocation, and hostel rules.",
    "Courses": "Syllabus, subjects, course codes, electives, credit requirements, and academic programs.",
    "Events": "College fests, cultural events, hackathons, technical symposia, sports tournaments, and conferences.",
}


@dataclass
class TopicResult:
    """Dataclass holding topic tracking result and confidence metrics."""

    active_topic: str
    topic_confidence: float
    action: str  # "Continue topic" | "Reset context"
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class TopicTracker:
    """Automated Topic Tracking & Context Continuity Engine."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.40,
    ) -> None:
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading Topic Tracker embedding model '{self.model_name}' on device '{device}'")
        self.model = SentenceTransformer(self.model_name, device=device)

        # Pre-compute category embeddings for zero-shot topic classification
        self.topic_names = list(TOPIC_DESCRIPTIONS.keys())
        descriptions = [f"{name}: {desc}" for name, desc in TOPIC_DESCRIPTIONS.items()]
        self.topic_embeddings = self.model.encode(
            descriptions,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        self.current_topic: Optional[str] = None
        self.previous_query: Optional[str] = None
        self.previous_embedding: Optional[np.ndarray] = None

    def detect_topic(self, query: str) -> Tuple[str, float]:
        """Classify user query into one of 10 campus topic categories."""
        query_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        similarities = np.dot(self.topic_embeddings, query_vec)
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        detected_topic = self.topic_names[best_idx]

        # Clamp confidence score to [0.0, 1.0]
        confidence = float(np.clip(round((best_score + 1.0) / 2.0, 4), 0.0, 1.0))
        return detected_topic, confidence

    def process_turn(
        self,
        query: str,
        previous_topic: Optional[str] = None,
        previous_query: Optional[str] = None,
    ) -> TopicResult:
        """Process turn query, detect active topic, and determine topic continuity action."""
        query_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        detected_topic, topic_confidence = self.detect_topic(query)

        prev_topic = previous_topic or self.current_topic
        prev_q = previous_query or self.previous_query

        action = "Reset context"
        similarity_score = 0.0

        if prev_q:
            prev_vec = self.model.encode(
                [prev_q],
                convert_to_numpy=True,
                normalize_embeddings=True,
            )[0]
            similarity_score = float(np.dot(prev_vec, query_vec))
            similarity_score = round(max(0.0, float(similarity_score)), 4)

            # Context continuation condition
            if similarity_score >= self.similarity_threshold or (prev_topic and prev_topic == detected_topic):
                action = "Continue topic"
            else:
                action = "Reset context"
        else:
            action = "Continue topic"
            similarity_score = 1.0

        # Update state
        self.current_topic = detected_topic
        self.previous_query = query
        self.previous_embedding = query_vec

        result = TopicResult(
            active_topic=detected_topic,
            topic_confidence=topic_confidence,
            action=action,
            similarity_score=similarity_score,
            metadata={
                "previous_topic": prev_topic,
                "previous_query": prev_q,
            },
        )

        logger.info(
            f"Topic Tracked: Active='{detected_topic}' (Conf: {topic_confidence:.4f}) | "
            f"Action='{action}' | SimScore: {similarity_score:.4f}"
        )
        return result
