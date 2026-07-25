# Phase 2 BVBCET / KLE Tech Production-Grade RAG Ingestion Pipeline

Modular, fault-tolerant, resumable web ingestion pipeline designed to discover, crawl, download, organize, and convert all publicly accessible HTML content and PDF documents from `https://www.kletech.ac.in/hubballi/` into Markdown documents for RAG systems.

## Project Structure

```text
bvbcet_rag_pipeline/
│
├── config/
│   ├── config.py           # Core configuration & pipeline parameters
│   ├── constants.py        # System constants & HTTP User-Agent
│   └── categories.py       # 18 Target category rules & definitions
│
├── crawler/
│   ├── crawler.py          # HTML page fetcher
│   ├── crawl_manager.py    # Main crawl orchestrator
│   ├── queue_manager.py    # Resumable URL queue manager
│   ├── link_extractor.py   # DOM link & PDF extractor
│   ├── url_normalizer.py   # Canonical URL normalizer
│   ├── robots_handler.py   # robots.txt compliance checker
│   ├── sitemap_parser.py   # sitemap.xml parser
│   ├── page_classifier.py  # Category detector
│   └── retry_handler.py    # Exponential backoff retry handler
│
├── downloader/
│   ├── pdf_downloader.py   # Raw PDF downloader into knowledge_base/pdf/
│   ├── asset_downloader.py # Asset downloader
│   └── download_manager.py # Download pool manager
│
├── converter/
│   ├── html_to_markdown.py # Noise stripping HTML-to-Markdown converter
│   ├── pdf_to_markdown.py  # Multi-tier PDF converter (Docling -> PyMuPDF -> PyPDF)
│   └── markdown_writer.py  # Category Markdown writer
│
├── metadata/
│   ├── metadata_generator.py # Page & PDF metadata dataclass creator
│   └── metadata_writer.py    # metadata.json manager
│
├── storage/
│   ├── folder_manager.py     # Knowledge base folder structure creator
│   ├── filename_generator.py # Collision-free title slug generator
│   └── duplicate_manager.py  # MD5 content hash deduplication
│
├── logger/
│   ├── logger.py           # Multi-handler logger (crawl.log, failed_pages.log, pdf_download.log)
│   └── statistics.py       # Live metrics & statistics.json output
│
├── utils/
│   ├── helpers.py          # String & date helpers
│   ├── url_utils.py        # Domain & parameter filtering
│   └── validation.py       # HTTP response validator
│
├── knowledge_base/
│   ├── markdown/           # 18 Category subfolders
│   ├── pdf/                # Raw original PDF files
│   ├── metadata/           # metadata.json
│   └── logs/               # crawl.log, failed_pages.log, pdf_download.log, statistics.json
│
├── pipeline.py             # Main execution entry point
├── requirements.txt        # System dependencies
└── README.md               # Project documentation
```

## Quick Start

```bash
# Run pipeline with resume support
python pipeline.py

# Run a fresh crawl (clear state)
python pipeline.py --fresh

# Override maximum pages safety ceiling
python pipeline.py --max-pages 500
```
