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

        import time
        logger = logging.getLogger(__name__)
        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in {documents_path}"
            )

        all_chunks: List[str] = []
        start_time = time.perf_counter()
        for pdf in pdf_files:
            logger.info("Loading PDF: %s", pdf.name)
            text = self.pdf_loader.load(str(pdf))
            chunks = self.text_chunker.chunk(text)
            all_chunks.extend(chunks)
        logger.info("Total chunks collected: %d", len(all_chunks))
        embeddings = self.embedding_model.encode(all_chunks)
        self.vector_store.create(
            texts=all_chunks,
            embeddings=embeddings,
        )
        self.vector_store.save()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Vector database created successfully in %.2f ms", elapsed_ms)
    def ingest_single_pdf(self, pdf_path: str) -> None:
        """
        Build the index from a single PDF.
        """
        import time
        logger = logging.getLogger(__name__)
        start_time = time.perf_counter()
        text = self.pdf_loader.load(pdf_path)
        chunks = self.text_chunker.chunk(text)
        embeddings = self.embedding_model.encode(chunks)
        self.vector_store.create(
            texts=chunks,
            embeddings=embeddings,
        )
        self.vector_store.save()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Vector database created successfully for %s in %.2f ms", pdf_path, elapsed_ms)        