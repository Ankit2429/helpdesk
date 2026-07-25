"""Text Chunker module for recursive text splitting."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class TextChunker:
    """Split text documents into optimized RAG chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """Split a list of LangChain documents into smaller chunks."""
        return self.splitter.split_documents(documents)
