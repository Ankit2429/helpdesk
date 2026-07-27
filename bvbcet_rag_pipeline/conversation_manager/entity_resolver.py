"""Production-Grade Entity Resolution Module.

Extracts campus entities (departments, faculty, buildings, hostles, etc.)
and resolves coreference pronouns ('he', 'she', 'his', 'her', 'their', 'it', 'there',
'that', 'this', 'those', 'previous department', 'previous building', 'previous faculty')
using conversation context history.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from logger.logger import get_logger

logger = get_logger("entity_resolver")

PRONOUNS_AND_REFERENCES: Set[str] = {
    "he",
    "she",
    "his",
    "her",
    "their",
    "it",
    "there",
    "that",
    "this",
    "those",
    "previous department",
    "previous building",
    "previous faculty",
}

# Regex pattern matching candidate pronouns and references
PRONOUN_PATTERN = re.compile(
    r"\b(previous department|previous building|previous faculty|he|she|his|her|their|it|there|that|this|those)\b",
    re.IGNORECASE,
)

KNOWN_CAMPUS_ENTITIES: Dict[str, List[str]] = {
    "department": [
        "Computer Science",
        "Artificial Intelligence",
        "Electronics and Communication",
        "Mechanical Engineering",
        "Civil Engineering",
        "Electrical Engineering",
        "Biotechnology",
        "Automobile Engineering",
    ],
    "building": [
        "Main Building",
        "B-Block",
        "BT Block",
        "Auditorium",
        "Central Library",
        "CS Department Building",
    ],
    "faculty": [
        "Dr. Ashok Shettar",
        "Prof. Kulkarni",
        "Dr. Patil",
        "Prof. Joshi",
    ],
    "hostel": [
        "Boys Hostel",
        "Girls Hostel",
        "Campus Hostel",
    ],
}


@dataclass
class EntityResult:
    """Dataclass holding entity resolution outputs and confidence score."""

    original_query: str
    resolved_query: str
    extracted_entities: Dict[str, str] = field(default_factory=dict)
    resolved_references: Dict[str, str] = field(default_factory=dict)
    entity_confidence: float = 1.0


class EntityResolver:
    """Coreference and Campus Entity Resolver Engine."""

    def __init__(self) -> None:
        self.context_entities: Dict[str, str] = {}
        self.turn_history: List[Dict[str, Any]] = []

    def extract_entities(self, text: str) -> Dict[str, str]:
        """Extract explicit campus entity mentions from text."""
        extracted: Dict[str, str] = {}
        for category, entities in KNOWN_CAMPUS_ENTITIES.items():
            for entity in entities:
                pattern = re.compile(rf"\b{re.escape(entity)}\b", re.IGNORECASE)
                if pattern.search(text):
                    extracted[category] = entity
                    break
        return extracted

    def update_context(self, text: str, entities: Optional[Dict[str, str]] = None) -> None:
        """Update active context entity registry from turn text."""
        found_entities = entities or self.extract_entities(text)
        for cat, val in found_entities.items():
            self.context_entities[cat] = val

    def resolve(
        self,
        query: str,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
    ) -> EntityResult:
        """Resolve pronouns and relative references in user query using conversation history."""
        # Update internal context registry if external conversation context is provided
        if conversation_context:
            for turn in conversation_context:
                turn_text = turn.get("question", "") + " " + turn.get("answer", "")
                self.update_context(turn_text)

        current_entities = self.extract_entities(query)
        self.update_context(query, current_entities)

        resolved_query = query
        resolved_refs: Dict[str, str] = {}
        confidence_factors: List[float] = []

        matches = list(PRONOUN_PATTERN.finditer(query))
        for match in matches:
            ref = match.group(0).lower()

            # Determine entity category mapping for the reference
            replacement: Optional[str] = None
            if "department" in ref:
                replacement = self.context_entities.get("department")
            elif "building" in ref:
                replacement = self.context_entities.get("building")
            elif "faculty" in ref or ref in ["he", "she", "his", "her"]:
                replacement = self.context_entities.get("faculty")
            elif ref in ["it", "that", "this"]:
                replacement = (
                    self.context_entities.get("department")
                    or self.context_entities.get("building")
                    or self.context_entities.get("hostel")
                )
            elif ref in ["there", "those"]:
                replacement = self.context_entities.get("building") or self.context_entities.get("hostel")

            if replacement:
                resolved_refs[ref] = replacement
                # Substitute reference in query
                resolved_query = re.sub(rf"\b{re.escape(match.group(0))}\b", replacement, resolved_query, count=1, flags=re.IGNORECASE)
                confidence_factors.append(0.95)
            else:
                confidence_factors.append(0.50)

        # Compute overall entity resolution confidence
        if not matches:
            entity_confidence = 1.0 if current_entities else 0.85
        else:
            entity_confidence = round(float(sum(confidence_factors) / len(confidence_factors)), 4)

        result = EntityResult(
            original_query=query,
            resolved_query=resolved_query,
            extracted_entities={**self.context_entities, **current_entities},
            resolved_references=resolved_refs,
            entity_confidence=entity_confidence,
        )

        logger.info(
            f"Entity Resolution: Original='{query}' -> Resolved='{resolved_query}' | "
            f"ResolvedRefs={resolved_refs} | Conf={entity_confidence:.4f}"
        )
        return result
