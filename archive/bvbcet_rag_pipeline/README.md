# Production-Grade BVBCET / KLE Tech RAG Ingestion & Semantic Chunking Pipeline

Autonomous, fault-tolerant, resumable web crawler, PDF converter, and Semantic Markdown Chunking Pipeline designed for RAG (Retrieval-Augmented Generation) systems. Target website: `https://www.kletech.ac.in/hubballi/`.

---

## 🚀 Execution Flow

```text
Crawler  ──►  Downloader  ──►  Markdown Generator  ──►  Semantic Chunker
```

1. **Crawler**: Recursively traverses domain URLs (respects `robots.txt`, handles `sitemap.xml`, strips tracking params).
2. **Downloader**: Stream-retrieves raw PDF documents directly into `knowledge_base/pdf/`.
3. **Markdown Generator**: Strips UI noise (headers, footers, popups, scripts) and converts HTML pages & PDFs into clean Markdown structured across 18 category subfolders.
4. **Semantic Chunker**: Preserves heading hierarchy and atomic blocks (tables, code blocks, lists, quotes, horizontal rules), performs SHA256 deduplication, and exports chunks into JSONL storage.

---

## 📁 Expected Folder Structure

```text
bvbcet_rag_pipeline/
│
├── config/                     # Pipeline configuration & 18 category definitions
│   ├── config.py
│   ├── constants.py
│   └── categories.py
│
├── crawler/                    # Async/Sync Crawler & Link Extractor
│   ├── crawler.py
│   ├── crawl_manager.py
│   ├── queue_manager.py
│   ├── link_extractor.py
│   ├── url_normalizer.py
│   ├── robots_handler.py
│   ├── sitemap_parser.py
│   ├── page_classifier.py
│   └── retry_handler.py
│
├── downloader/                 # Raw PDF & Asset Downloader
│   ├── pdf_downloader.py
│   ├── asset_downloader.py
│   └── download_manager.py
│
├── converter/                  # HTML & Multi-tier PDF Converters
│   ├── html_to_markdown.py
│   ├── pdf_to_markdown.py
│   └── markdown_writer.py
│
├── chunker/                    # Semantic Markdown Chunking Engine
│   ├── semantic_chunker.py
│   ├── metadata.py
│   └── chunker.py
│
├── metadata/                   # Metadata Generator & JSON Writer
│   ├── metadata_generator.py
│   └── metadata_writer.py
│
├── storage/                    # Folder & Title Slugification Utilities
│   ├── folder_manager.py
│   ├── filename_generator.py
│   └── duplicate_manager.py
│
├── logger/                     # Multi-Handler Loggers & Statistics Tracker
│   ├── logger.py
│   └── statistics.py
│
├── utils/                      # Helper Functions & URL Validation
│   ├── helpers.py
│   ├── url_utils.py
│   └── validation.py
│
├── knowledge_base/             # Knowledge Base Output Directory
│   ├── markdown/               # 18 Category folders containing clean .md files
│   ├── pdf/                    # Raw original downloaded PDF files
│   ├── chunks/                 # Generated chunks storage
│   │   ├── chunks.jsonl        # Output JSONL chunk records for vector embedding
│   │   ├── duplicate_chunks.json
│   │   └── statistics.json
│   ├── metadata/
│   │   └── metadata.json       # Master metadata catalog
│   └── logs/
│       ├── crawl.log
│       ├── failed_pages.log
│       ├── pdf_download.log
│       └── statistics.json
│
├── tests/                      # Pytest Unit & Integration Test Suite
│   ├── test_pipeline.py
│   ├── test_semantic_chunker.py
│   ├── test_chunk_metadata.py
│   ├── test_chunker_runner.py
│   └── test_chunker.py
│
├── pipeline.py                 # Main execution entry point
├── requirements.txt            # Project dependencies
└── README.md                   # System documentation
```

---

## 💻 How to Run

### 1. Full Pipeline Execution (Crawler + Downloader + Markdown + Chunker)

```bash
# Run full pipeline with automatic state resume support
python pipeline.py

# Start a fresh ingestion & chunking run (clears previous state)
python pipeline.py --fresh

# Set safety ceiling for maximum pages to crawl
python pipeline.py --max-pages 1000
```

### 2. Standalone Semantic Chunker CLI

To run only the Semantic Chunking engine over existing Markdown files:

```bash
# Process default input directory (knowledge_base/markdown) into chunks/
python -m chunker.chunker

# Specify custom input and output paths with custom token parameters
python -m chunker.chunker --input knowledge_base/markdown --output chunks --chunk-size 750 --chunk-overlap 150
```

---

## 💻 CLI Examples

```bash
# Example 1: Fresh run with 500 pages limit
python pipeline.py --fresh --max-pages 500

# Example 2: Run chunker on custom markdown directory
python -m chunker.chunker -i ../bvbcet_scraper/knowledge_base/markdown -o custom_chunks --chunk-size 600 --chunk-overlap 100
```

---

## 🛠️ Troubleshooting & Common Fixes

### 1. File Locks on Windows (`PermissionError [WinError 32]`)
* **Symptom**: `PermissionError` when `--fresh` attempts to delete locked log files.
* **Fix**: The pipeline handles safe file unlinking (`target_file.unlink()`) wrapped in try/except blocks.

### 2. PDF Conversion Fallback
* **Behavior**: Uses Tier 1 **Docling** -> Tier 2 **PyMuPDF4LLM** -> Tier 3 **PyPDF**.
* **Note**: Corrupted or empty PDFs are logged in `failed_pages.log` and skipped automatically without interrupting pipeline execution.

### 3. Duplicate Chunks
* **Behavior**: SHA256 digests are computed for every chunk text. Duplicate chunks are logged in `chunks/duplicate_chunks.json` and excluded from `chunks/chunks.jsonl`.
