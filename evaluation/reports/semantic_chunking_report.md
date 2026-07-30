# Semantic Section-Aware Chunking & Metadata Engineering Report

**Timestamp**: `2026-07-29T17:56:05Z`  
**System Evaluated**: Offline AI Campus Helpdesk Robot — Semantic Document Chunker  
**Evaluation Scope**: 1,014 QA Queries across 8 Domain Categories  

---

## 1. Old Architecture vs. New Architecture

### Old Architecture (Fixed Character Chunking)

```
Markdown Files (432 Docs)
  │
  ▼
RecursiveCharacterTextSplitter (Fixed 800 chars, 120 overlap)
  │
  ▼
11,440 Arbitrary Text Chunks (26.5 chunks / doc)
  │
  ▼
Flat Metadata (Only basic source filename, no breadcrumbs)
```

- **Drawbacks**:
  - Tables, bullet lists, numbered lists, and code blocks were cut mid-sentence across chunk boundaries.
  - Sub-section chunks lost parent context (e.g., fee amounts without knowing which program they belonged to).
  - High storage footprint and vector search dilution (11,440 chunks).

---

### New Architecture (Semantic Section-Aware Chunking + Hierarchical Metadata)

```
Markdown Files (432 Docs)
  │
  ▼
MarkdownSemanticChunker (Block-Level Parser: Headers, Tables, Lists, Code, Paras)
  │
  ▼
Hierarchical Section Grouping + Small Section Merging (Target ~1500 chars)
  │
  ▼
Metadata Breadcrumb Context Injection ([Location: H1 > H2 > H3] prepended to content)
  │
  ▼
4,031 Clean Semantic Section Chunks (9.33 chunks / doc)
```

- **Key Advantages**:
  - **Zero Table & List Splitting**: Markdown tables, bullet lists, numbered lists, and code blocks remain 100% intact within single chunks.
  - **Hierarchical Breadcrumbs**: Every chunk prepends explicit location context (`[Location: Page Title > Section > Sub-section]`).
  - **65% Storage Reduction**: 4,031 high-quality chunks replace 11,440 fragmented chunks.

---

## 2. Metadata Schema

Every generated `KnowledgeDocument` chunk contains the following complete metadata schema:

| Metadata Field | Data Type | Example Value | Description |
| :--- | :--- | :--- | :--- |
| `source_filename` | `str` | `admission_for_ug_program_15515b.md` | Canonical source Markdown filename |
| `page_title` | `str` | `Admission for UG Program` | Main document title (H1 header or filename) |
| `section_title` | `str` | `Eligibility Criteria` | Nearest parent section header (H2 / H3) |
| `breadcrumb` | `str` | `Admission for UG Program > Undergraduate > Eligibility Criteria` | Complete hierarchical location breadcrumb path |
| `department` | `str` | `Admissions & Registrar Cell` | Inferred academic or administrative department |
| `chunk_number` | `int` | `1` | 1-indexed chunk counter per source document |
| `parent_document` | `str` | `admission_for_ug_program_15515b.md` | Original parent source document identifier |
| `document_type` | `str` | `markdown` | Knowledge source document type (`markdown` or `pdf_converted`) |
| `heading_level` | `str` | `H2` | Structural heading level of the section (`H1`, `H2`, `H3`, etc.) |

---

## 3. Benchmark Metric Comparison

| Benchmark Metric | Baseline (Fixed 800 Chunks) | Phase 1 (Dedup + Candidate N=25) | Phase 2 (Semantic Section Chunking) | Net Improvement over Baseline |
| :--- | :---: | :---: | :---: | :---: |
| **Recall@1** | 38.36% | 40.24% | **43.49%** | **`+5.13%`** |
| **Recall@3** | 52.07% | 56.11% | **61.34%** | **`+9.27%`** |
| **Recall@5** | 56.21% | 60.85% | **65.29%** | **`+9.08%`** |
| **Mean Reciprocal Rank (MRR)** | 0.4550 | 0.4848 | **0.5265** | **`+0.0715`** |
| **Success Rate (Top-5 Match)** | 56.21% | 60.85% | **65.29%** | **`+9.08%`** |
| **Failed Queries Count** | 444 | 397 | **352** | **`-92 failed queries`** |
| **Total Vector Chunks** | 11,440 | 11,440 | **4,031** | **`-64.8% chunks`** |

---

## 4. Implementation Details

1. **`MarkdownSemanticChunker` ([markdown_chunker.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/rag/markdown_chunker.py))**:
   - Built a block-level Markdown parser recognizing headers (`#`, `##`, `###`), fenced code blocks (` ``` `), markdown table pipes (`| ... |`), bullet lists (`- `, `* `), and numbered lists (`1. `, `2. `).
   - Enforced strict atomic non-splitting rules for tables, code blocks, and list groups.
   - Built an active header state tracker computing breadcrumb paths (`H1 > H2 > H3`).
   - Implemented small section merging (sections under 250 characters are automatically joined with adjacent section blocks).
   - Added `[Location: Breadcrumb]` header prefixing to chunk text before vector embedding generation.

2. **`SemanticDocumentChunker` ([semantic_chunker.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/rag/semantic_chunker.py))**:
   - Integrated `MarkdownSemanticChunker` as the default chunker for all Markdown knowledge base documents.

3. **FAISS Vector Index Rebuild**:
   - Rebuilt FAISS index (`index.faiss`, `index.pkl`, `index-manifest.json`) from `data/canonical_markdown`.
   - Indexed 4,031 384-dimensional dense vectors with enriched breadcrumb content.

---

## 5. Expected Future Improvements

1. **RRF Weight Calibration (BM25 vs. Dense)**:
   - Adjust Reciprocal Rank Fusion (RRF) smoothing parameter ($k=20$) and increase BM25 keyword weight to capture exact institutional acronyms ("MCA", "NIRF", "DASA").
2. **Conversational Query Synonym Mapping**:
   - Map informal first-time visitor vocabulary ("apply for course", "tuition cost") to formal document headers ("Admission Eligibility", "Course Fee Structure").
3. **Multi-Target Dataset Annotation**:
   - Resolve dataset ambiguity where multiple equivalent department overview documents satisfy broad questions.

---

## 6. List of Every Modified File

- **[src/campus_helpdesk/infrastructure/rag/markdown_chunker.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/rag/markdown_chunker.py)**: Implemented block-level Markdown parser, table/list preservation logic, breadcrumb state tracker, and context header prepending.
- **[src/campus_helpdesk/infrastructure/rag/semantic_chunker.py](file:///d:/AUNTII/src/campus_helpdesk/infrastructure/rag/semantic_chunker.py)**: Connected `MarkdownSemanticChunker` into composite document chunking pipeline.
- **[data/faiss/](file:///d:/AUNTII/data/faiss/)**: Rebuilt FAISS vector store (`index.faiss`, `index.pkl`, `index-manifest.json`) containing 4,031 semantic section chunks.
- **[evaluation/reports/semantic_chunking_report.md](file:///d:/AUNTII/evaluation/reports/semantic_chunking_report.md)**: Generated comprehensive implementation & benchmark evaluation report.
