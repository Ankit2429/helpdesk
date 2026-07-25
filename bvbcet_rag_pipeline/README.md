# BVBCET / KLE Tech Campus RAG Pipeline

Modular web crawling, document downloading, html/pdf-to-markdown conversion, text cleaning, chunking, embedding, and FAISS vector database pipeline for BVBCET / KLE Technological University, Hubballi.

## Architecture & Directory Structure

```text
bvbcet_rag_pipeline/
│
├── crawler/         # Web crawling & URL extraction
├── downloader/      # HTML and PDF file downloader
├── converter/       # HTML & PDF -> Clean Markdown converter
├── cleaner/         # Text normalization & noise stripping
├── chunker/         # Recursive text chunking
├── embeddings/      # HuggingFace / SentenceTransformer embeddings
├── vector_db/       # FAISS vector database persistence & search
├── raw/             # Raw downloaded assets
│   ├── html/
│   └── pdf/
├── markdown/        # Processed clean markdown documents
├── tests/           # Unit and integration tests
├── config.py        # Central configuration settings
├── pipeline.py      # Main pipeline orchestration entrypoint
├── requirements.txt # Dependencies
└── README.md        # Documentation
```

## Setup & Running

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the end-to-end pipeline:
   ```bash
   python pipeline.py
   ```

3. Run tests:
   ```bash
   pytest
   ```
