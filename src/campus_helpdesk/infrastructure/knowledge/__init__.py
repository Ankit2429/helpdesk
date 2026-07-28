"""Modular Knowledge Base Normalization Infrastructure."""

from campus_helpdesk.infrastructure.knowledge.duplicate_detector import DuplicateDetector
from campus_helpdesk.infrastructure.knowledge.metadata_extractor import MetadataExtractor
from campus_helpdesk.infrastructure.knowledge.pipeline import KnowledgeNormalizationPipeline
from campus_helpdesk.infrastructure.knowledge.text_cleaner import MarkdownTextCleaner

__all__ = [
    "MetadataExtractor",
    "MarkdownTextCleaner",
    "DuplicateDetector",
    "KnowledgeNormalizationPipeline",
]
