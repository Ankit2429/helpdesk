"""Configuration module for BVBCET RAG Pipeline."""

from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
RAW_HTML_DIR = RAW_DIR / "html"
RAW_PDF_DIR = RAW_DIR / "pdf"
MARKDOWN_DIR = BASE_DIR / "markdown"
VECTOR_DB_DIR = BASE_DIR / "vector_db"

# Ensure directories exist
for path in [RAW_HTML_DIR, RAW_PDF_DIR, MARKDOWN_DIR, VECTOR_DB_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Crawler Settings
START_URLS = [
    "https://www.kletech.ac.in",
]
ALLOWED_DOMAINS = [
    "kletech.ac.in",
    "bvb.edu",
]
MAX_DEPTH = 3
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 15

# Chunker Settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80

# Embedding & Vector Store Settings
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
FAISS_INDEX_NAME = "bvbcet_index"
