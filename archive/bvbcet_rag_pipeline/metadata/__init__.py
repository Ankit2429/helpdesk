"""Metadata package initialization."""

from metadata.metadata_generator import MetadataGenerator, PageMetadata
from metadata.metadata_writer import MetadataWriter

__all__ = [
    "PageMetadata",
    "MetadataGenerator",
    "MetadataWriter",
]
