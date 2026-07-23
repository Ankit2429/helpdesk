"""Configurable LangChain text chunking adapter."""

from collections.abc import Sequence

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from campus_helpdesk.domain.knowledge import KnowledgeDocument


class RecursiveTextChunker:
    """Split knowledge documents into overlapping recursive text chunks."""

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: Sequence[str],
        add_start_index: bool,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=list(separators),
            add_start_index=add_start_index,
        )

    def split(self, documents: Sequence[KnowledgeDocument]) -> list[KnowledgeDocument]:
        """Split documents and preserve their metadata for citations."""
        langchain_documents = [
            Document(page_content=document.content, metadata=dict(document.metadata)) for document in documents
        ]
        chunks = self._splitter.split_documents(langchain_documents)
        return [
            KnowledgeDocument(
                content=chunk.page_content,
                metadata={str(key): str(value) for key, value in chunk.metadata.items()},
            )
            for chunk in chunks
        ]
