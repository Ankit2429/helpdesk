# KLE Technological University (BVBCET) Website Ingestion Pipeline

Production-grade website crawler and RAG ingestion pipeline designed to discover, download, clean, categorize, and convert all publicly accessible pages and PDFs from `https://www.kletech.ac.in/hubballi/` into Markdown documents.

## Output Directory Structure (`knowledge_base/`)

```text
knowledge_base/
├── markdown/
│   ├── about/
│   ├── admissions/
│   ├── academics/
│   ├── departments/
│   ├── placements/
│   ├── faculty/
│   ├── research/
│   ├── infrastructure/
│   ├── library/
│   ├── hostel/
│   ├── transport/
│   ├── examination/
│   ├── downloads/
│   ├── notices/
│   ├── events/
│   ├── gallery/
│   ├── contact/
│   └── miscellaneous/
├── pdf/
├── metadata/
│   └── metadata.json
└── logs/
    ├── crawl.log
    ├── failed_pages.log
    ├── pdf_download.log
    └── statistics.json
```

## Features

- **Recursive Link Discovery**: Automatically traverses navigation menus, footers, sidebars, department pages, and notices under `kletech.ac.in`.
- **Noise Removal**: Strips header/footer menus, navbars, sidebars, cookie banners, and scripts while preserving headings, lists, tables, and links.
- **PDF Conversion**: Downloads raw PDFs into `knowledge_base/pdf/` and converts them using Docling (with PyMuPDF4LLM and PyPDF fallbacks).
- **Metadata Generation**: Writes comprehensive JSON metadata (`url`, `category`, `crawl_time`, `word_count`, `content_type`, etc.) into `knowledge_base/metadata/metadata.json`.
- **State Checkpointing & Resume**: Maintains persistent JSON state so runs can be safely interrupted and resumed without re-downloading duplicate pages.

## Usage

```bash
# Run pipeline with resume support
python main.py

# Run fresh pipeline (clear previous state)
python main.py --fresh

# Override maximum pages safety ceiling
python main.py --max-pages 500
```
