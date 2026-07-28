# Knowledge Base Data Quality Report

This report evaluates the scraped Markdown knowledge base located in `archive/bvbcet_scraper/knowledge_base/markdown/` to assess its readiness for production RAG ingestion.

## Executive Summary

The scraped dataset suffers from **severe semantic duplication**. While the file hashes appear unique due to differing Source URLs injected by the scraper, stripping the URLs reveals that **88.4% of the dataset consists of identical duplicate documents**. Removing these duplicates will drastically improve LLM retrieval accuracy and reduce embedding costs/time.

## 1. Quantitative Analysis

| Metric | Value | Notes |
| :--- | :--- | :--- |
| **Total Markdown Files** | 4,746 | |
| **Total Size** | 37.44 MB | Uncompressed text. |
| **Duplicate Documents (Exact Hash)** | 0 | Source URLs cause exact hash mismatch. |
| **Near-Duplicate (Semantic) Documents** | 4,198 | Stripping URLs and headers reveals identical content. |
| **Unique Canonical Documents** | 548 | The actual number of distinct pages. |
| **Empty Files** | 0 | |
| **Tiny Files (< 1 KB)** | 99 | Likely stub pages, error pages, or useless index files. |
| **Oversized Files (> 100 KB)** | 69 | Highly likely to exceed LLM chunking limits effectively, usually raw PDF text dumps containing massive curriculum tables. |

## 2. Content Quality Analysis

* **Missing Metadata (100%):** None of the 4,746 files contain YAML frontmatter (e.g., `--- \n title: ... \n ---`). This deprives the RAG pipeline of critical routing and citation data.
* **Missing Titles (0%):** All files start with an H1 header (`# title`), which is good for text chunkers.
* **Broken Markdown (0%):** No unbalanced code blocks (` ``` `) were detected.
* **PDF Artifacts (~10%):** At least 470 documents display signs of raw PDF dumping (e.g., repeating whitespace blocks, "Scanned by", etc.).
* **Navigation Noise (0%):** The scraper successfully isolated main body content; traditional website headers/footers were not detected in the raw text.

## 3. Structural Recommendations

### 3.1 Files That Should Be Excluded
- **Tiny Files:** The 99 files `< 1 KB` (e.g., `home_baca25.md`) offer insufficient context for RAG and should be discarded.
- **Duplicate "Programs":** The analysis script identified **4,009 duplicate variants** of `programs_*.md`. The scraper crawled deep pagination or tag links, capturing the exact same curriculum lists thousands of times.

### 3.2 Files That Should Be Split
- **Oversized Files:** The 69 files `> 100 KB` (e.g., `bachelor-computer-science-engineering-curriculum-2022-2026.md`) are too large. They contain entire 4-year curriculum tables. They should be split into smaller markdown files per semester or per topic, otherwise standard Langchain text splitters will sever semantic relationships inside tables.

### 3.3 Pages That Should Be Merged
- Contact directories scattered across multiple tiny faculty files should be merged into a single `faculty_directory.md` to prevent the vector store from returning heavily fragmented context blocks.

## 4. Proposed Canonical Folder Taxonomy

```text
data/canonical_markdown/
├── academics/
│   ├── ug_curriculum/       # Split by department (CSE, ECE, MECH)
│   ├── pg_curriculum/
│   └── academic_calendar.md
├── admissions/
│   ├── ug_admissions.md
│   ├── pg_admissions.md
│   ├── fee_structure.md
│   └── faq.md
├── campus_life/
│   ├── library.md
│   ├── hostels.md
│   └── facilities.md
├── departments/             # Specific contact info, HOD details
└── research_and_placements/
```

## 5. Estimated Optimization Reductions

| Optimization Metric | Before Cleanup | After Cleanup (Estimated) | Reduction |
| :--- | :--- | :--- | :--- |
| **Total Files** | 4,746 | ~548 | **-88.4%** |
| **Dataset Size** | 37.44 MB | ~24.23 MB | **-35.3%** |
| **Vector Embeddings** | ~95,000 chunks | ~11,000 chunks | **-88.4%** |

*Note: The massive reduction in embeddings will directly translate to faster FAISS build times, smaller RAM footprints on the Raspberry Pi, and the elimination of "hallucinations" caused by the LLM retrieving 4 identical copies of the same document instead of diverse context.*
