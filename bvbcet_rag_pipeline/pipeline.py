"""BVBCET RAG Pipeline main orchestrator."""

import logging
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader

from config import (
    RAW_HTML_DIR,
    RAW_PDF_DIR,
    MARKDOWN_DIR,
    VECTOR_DB_DIR,
    START_URLS,
    ALLOWED_DOMAINS,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL_NAME,
    FAISS_INDEX_NAME,
)
from crawler.crawler import CampusCrawler
from downloader.downloader import ResourceDownloader
from converter.converter import DocumentConverter
from cleaner.cleaner import TextCleaner
from chunker.chunker import TextChunker
from embeddings.embeddings import EmbeddingManager
from vector_db.vector_db import VectorDBManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("BVBCET_RAG_Pipeline")


def run_pipeline() -> None:
    """Execute the end-to-end RAG ingestion pipeline."""
    logger.info("Starting BVBCET RAG Pipeline...")

    # 1. Crawl URLs
    logger.info("Step 1: Crawling URLs...")
    crawler = CampusCrawler(start_urls=START_URLS, allowed_domains=ALLOWED_DOMAINS, max_depth=1)
    url_map = crawler.crawl()
    logger.info(f"Discovered {len(url_map['html'])} HTML pages and {len(url_map['pdf'])} PDF documents.")

    # 2. Download Content
    logger.info("Step 2: Downloading assets...")
    downloader = ResourceDownloader(html_dir=RAW_HTML_DIR, pdf_dir=RAW_PDF_DIR)
    
    html_files = []
    for url in url_map["html"]:
        path = downloader.download_html(url)
        if path:
            html_files.append(path)

    pdf_files = []
    for url in url_map["pdf"]:
        path = downloader.download_pdf(url)
        if path:
            pdf_files.append(path)

    # 3. Convert to Markdown
    logger.info("Step 3: Converting to Markdown...")
    converter = DocumentConverter(output_markdown_dir=MARKDOWN_DIR)
    markdown_files = []

    for html_path in html_files:
        md_path = converter.convert_html_to_markdown(html_path)
        if md_path:
            markdown_files.append(md_path)

    for pdf_path in pdf_files:
        md_path = converter.convert_pdf_to_markdown(pdf_path)
        if md_path:
            markdown_files.append(md_path)

    # 4. Clean Markdown Documents
    logger.info("Step 4: Cleaning text documents...")
    for md_file in MARKDOWN_DIR.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            cleaned_content = TextCleaner.clean_text(content)
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(cleaned_content)
        except Exception as e:
            logger.warning(f"Error cleaning {md_file}: {e}")

    # 5. Load and Chunk Documents
    logger.info("Step 5: Loading and chunking markdown documents...")
    loader = DirectoryLoader(str(MARKDOWN_DIR), glob="**/*.md", loader_cls=TextLoader)
    documents = loader.load()

    if not documents:
        logger.warning("No markdown documents found to ingest. Pipeline complete.")
        return

    chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = chunker.chunk_documents(documents)
    logger.info(f"Generated {len(chunks)} text chunks from {len(documents)} document(s).")

    # 6. Embed and Index into Vector DB
    logger.info("Step 6: Building FAISS Vector Index...")
    embedding_mgr = EmbeddingManager(model_name=EMBEDDING_MODEL_NAME)
    vector_mgr = VectorDBManager(db_dir=VECTOR_DB_DIR, embeddings=embedding_mgr.get_embeddings())
    vector_mgr.build_and_save(chunks, index_name=FAISS_INDEX_NAME)

    logger.info("BVBCET RAG Pipeline completed successfully!")


if __name__ == "__main__":
    run_pipeline()
