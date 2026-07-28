"""Markdown-aware semantic chunking adapter."""

from collections.abc import Sequence

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from campus_helpdesk.domain.knowledge import KnowledgeDocument


class MarkdownSemanticChunker:
    """Split Markdown documents semantically by headers while preserving section hierarchy."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        headers_to_split_on: Sequence[tuple[str, str]] | None = None,
    ) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._headers_to_split_on = headers_to_split_on or [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        self._header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=list(self._headers_to_split_on),
            strip_headers=False,
        )
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def split_document(self, document: KnowledgeDocument) -> list[KnowledgeDocument]:
        """Split a single Markdown KnowledgeDocument semantically into smaller chunks."""
        header_docs = self._header_splitter.split_text(document.content)

        final_chunks: list[KnowledgeDocument] = []
        for h_doc in header_docs:
            if len(h_doc.page_content) > self._chunk_size:
                sub_chunks = self._text_splitter.split_documents([h_doc])
                for sc in sub_chunks:
                    merged_meta = {
                        **dict(document.metadata),
                        **{str(k): str(v) for k, v in sc.metadata.items()},
                    }
                    final_chunks.append(KnowledgeDocument(content=sc.page_content, metadata=merged_meta))
            else:
                merged_meta = {
                    **dict(document.metadata),
                    **{str(k): str(v) for k, v in h_doc.metadata.items()},
                }
                final_chunks.append(KnowledgeDocument(content=h_doc.page_content, metadata=merged_meta))

        return final_chunks
