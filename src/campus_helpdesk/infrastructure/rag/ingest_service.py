"""
Ingest Service

Builds the FAISS vector database from campus documents.

Pipeline:
PDFs
    ↓
PDF Loader
    ↓
Text Chunker
    ↓
Embedding Model
    ↓
FAISS Store
"""

from pathlib import Path
from typing import List

from campus_helpdesk.infrastructure.rag.pdf_loader import PDFLoader
from campus_helpdesk.infrastructure.rag.text_chunker import TextChunker
from campus_helpdesk.infrastructure.rag.sentence_transformer import SentenceTransformerEmbedding
from campus_helpdesk.infrastructure.rag.faiss_store import FaissStore


class IngestService:
    """
    Responsible for creating the vector database.
    """

    def __init__(
        self,
        pdf_loader: PDFLoader,
        text_chunker: TextChunker,
        embedding_model: SentenceTransformerEmbedding,
        vector_store: FaissStore,
    ):
        self.pdf_loader = pdf_loader
        self.text_chunker = text_chunker
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def ingest_directory(self, documents_path: str) -> None:
        """
        Load every PDF inside a directory and build the FAISS index.
        """

        pdf_files = list(Path(documents_path).glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in {documents_path}"
            )

        all_chunks: List[str] = []

        for pdf in pdf_files:
            print(f"Loading: {pdf.name}")

            text = self.pdf_loader.load(str(pdf))

            chunks = self.text_chunker.chunk(text)

            all_chunks.extend(chunks)

        print(f"Total Chunks: {len(all_chunks)}")

        embeddings = self.embedding_model.encode(all_chunks)

        self.vector_store.create(
            texts=all_chunks,
            embeddings=embeddings,
        )

        self.vector_store.save()

        print("Vector database created successfully.")

    def ingest_single_pdf(self, pdf_path: str) -> None:
        """
        Build the index from a single PDF.
        """

        text = self.pdf_loader.load(pdf_path)

        chunks = self.text_chunker.chunk(text)

        embeddings = self.embedding_model.encode(chunks)

        self.vector_store.create(
            texts=chunks,
            embeddings=embeddings,
        )

        self.vector_store.save()

        print("Vector database created successfully.")
        