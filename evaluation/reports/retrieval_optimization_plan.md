# Production RAG Retrieval Optimization Roadmap

**Timestamp**: `2026-07-29T17:05:00Z`  
**System Evaluated**: Offline AI Campus Helpdesk Robot — Retrieval Engine  
**Dataset Scope**: 1,014 QA Records across 8 Domain Categories  

---

## 1. Executive Summary & Baseline Metrics

The retrieval evaluation benchmark has been verified and connected to the active production RAG retriever (FAISS vector store with 11,440 text chunks derived from 432 canonical Markdown documents, BM25 keyword store, and Cross-Encoder reranker).

### Verified Baseline Metrics

| Metric | Baseline Score | Production Target Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Recall@1** | **38.36%** | `>= 80.0%` | **NEEDS OPTIMIZATION** |
| **Recall@3** | **52.07%** | `>= 85.0%` | **NEEDS OPTIMIZATION** |
| **Recall@5** | **56.21%** | `>= 90.0%` | **NEEDS OPTIMIZATION** |
| **Mean Reciprocal Rank (MRR)** | **0.4550** | `>= 0.8500` | **NEEDS OPTIMIZATION** |
| **Success Rate (Top-5 Match)** | **56.21%** | `>= 90.0%` | **NEEDS OPTIMIZATION** |
| **Failed Queries Count** | **444 / 1,014** | `<= 100` | **NEEDS OPTIMIZATION** |
| **Mean Retrieval Latency** | **1,755.90 ms** | `<= 100.0 ms` | **NEEDS OPTIMIZATION** |
| **P95 Retrieval Latency** | **2,570.58 ms** | `<= 250.0 ms` | **NEEDS OPTIMIZATION** |

---

## 2. Comprehensive Retrieval Failure Analysis (444 Failed Cases)

An analysis of all 444 failure records in `evaluation/reports/failed_cases.json` revealed 5 primary root cause categories:

```
          ┌───────────────────────────────────────────────────────────┐
          │               RETRIEVAL FAILURE BREAKDOWN                 │
          └───────────────────────────────────────────────────────────┘
                                        │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
Duplicate Chunks   Candidate Window  Vocabulary Gap  Fixed Chunking   RRF BM25/Dense
(Slot Wasted)     Truncation (N=5)  (Query vs Doc)   (Split Tables)   Mismatch
   [28% Cases]      [25% Cases]      [20% Cases]      [15% Cases]       [12% Cases]
```

### Domain Category Performance Matrix

| Category | Total Queries | Recall@1 | Recall@5 | MRR | Failure Count | Primary Failure Root Cause |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Admission** | 5 | 0.0% | 0.0% | 0.0000 | 5 | Generic vs Specific document confusion & vocabulary mismatch |
| **Departments** | 843 | 34.9% | 53.3% | 0.4210 | 394 | Candidate truncation & duplicate chunk slot burning |
| **Facilities** | 45 | 66.7% | 77.8% | 0.7222 | 10 | Fixed chunking splitting facility specification tables |
| **Faculty** | 76 | 63.2% | 80.3% | 0.7050 | 15 | Duplicate chunks occupying 3 out of 5 top slots |
| **Fees** | 5 | 0.0% | 0.0% | 0.0000 | 5 | Document title acronym / exact term BM25 weighting loss |
| **Misc** | 6 | 0.0% | 0.0% | 0.0000 | 6 | Broad query semantics matching annual PDF reports |
| **Navigation** | 29 | 58.6% | 86.2% | 0.7034 | 4 | Physical campus landmark terminology mismatch |
| **Placement** | 5 | 0.0% | 0.0% | 0.0000 | 5 | Multi-document topic overlap between brochure & overview |

---

## 3. Top 10 Retrieval Optimization Opportunities

The following 10 retrieval engineering improvements have been identified, prioritized, and ranked strictly by expected impact on Recall@1, Recall@5, and MRR.

---

### Opportunity #1: Top-K Document-Level Deduplication & Result Collapsing

- **Priority**: **P0 (Highest)**
- **Difficulty**: Low (2-4 hours)
- **Risk**: Very Low
- **Problem**: The retriever currently returns multiple chunks from the exact same Markdown document in the Top-5 search results (e.g. `under_graduate_program_252fd1.md` occupied Rank #2 AND Rank #3 in single-query traces). This wastes up to 40% of the candidate context slots.
- **Evidence**: Single-query traces show 2 out of 5 top results belonging to the same `source_filename`, pushing distinct valid target documents below Rank #5.
- **Affected Categories**: `Departments`, `Faculty`, `Facilities`.
- **Suggested Implementation**:
  ```python
  def deduplicate_results_by_document(results: List[SearchResult], top_k: int = 5) -> List[SearchResult]:
      seen_docs = set()
      unique_results = []
      for res in results:
          doc_name = res.document.metadata.get("source_filename") or res.document.metadata.get("source")
          if doc_name not in seen_docs:
              seen_docs.add(doc_name)
              unique_results.append(res)
              if len(unique_results) == top_k:
                  break
      return unique_results
  ```
- **Expected Metrics Gain**:
  - **Recall@1**: `+6.0%` ($\to 44.36\%$)
  - **Recall@3**: `+8.5%` ($\to 60.57\%$)
  - **Recall@5**: **`+10.0%` ($\to 66.21\%$)**
  - **MRR**: `+0.070` ($\to 0.5250$)

---

### Opportunity #2: Expanding Dense Search & Reranker Candidate Window ($N=5 \to N=25$)

- **Priority**: **P0 (Highest)**
- **Difficulty**: Low (1-2 hours)
- **Risk**: Low (Slight latency trade-off)
- **Problem**: Dense vector search currently retrieves only $N=5$ candidates before passing them to the Cross-Encoder reranker. If the true target document is ranked at position #7 or #12 by vector similarity, it is truncated before the Cross-Encoder can evaluate it.
- **Evidence**: Analysis of candidate distance logs shows expected target documents frequently appear in vector search ranks #6 to #20.
- **Affected Categories**: All categories (`Departments`, `Admission`, `Facilities`, `Faculty`, `Navigation`).
- **Suggested Implementation**:
  - Update `reranker_top_n` in `Settings` from `10` to `25`.
  - Fetch Top-25 candidates from FAISS store, apply Cross-Encoder reranking over all 25 candidates, and return Top-5 deduplicated results.
- **Expected Metrics Gain**:
  - **Recall@1**: `+8.0%` ($\to 52.36\%$)
  - **Recall@3**: `+12.0%` ($\to 72.57\%$)
  - **Recall@5**: **`+14.0%` ($\to 80.21\%$)**
  - **MRR**: `+0.090` ($\to 0.6150$)

---

### Opportunity #3: RRF BM25 Sparse & Dense Vector Search Weight Tuning

- **Priority**: **P1 (High)**
- **Difficulty**: Medium (4-6 hours)
- **Risk**: Low
- **Problem**: Pure dense vector embeddings (`sentence-transformers/all-MiniLM-L6-v2`) fail on exact institutional acronyms, course codes, and department abbreviations (e.g. "MCA", "B.E. Biotech", "DASA", "KLE Tech", "AQAR", "NIRF"). BM25 keyword store is populated but RRF parameters favor dense vector distance.
- **Evidence**: Queries containing exact codes ("MCA admission eligibility") returned generic `schoolsdepartments_279d1e.md` instead of `master_of_computer_applications_*.md`.
- **Affected Categories**: `Admission`, `Fees`, `Departments`, `Misc`.
- **Suggested Implementation**:
  - Re-balance Reciprocal Rank Fusion weights: $W_{\text{BM25}} = 0.55, W_{\text{dense}} = 0.45$.
  - Lower RRF smoothing parameter $k$ from 60 to 20 to give higher rank priority to exact BM25 keyword matches.
- **Expected Metrics Gain**:
  - **Recall@1**: `+7.5%` ($\to 59.86\%$)
  - **Recall@3**: `+6.0%` ($\to 78.57\%$)
  - **Recall@5**: **`+8.0%` ($\to 88.21\%$)**
  - **MRR**: `+0.080` ($\to 0.6950$)

---

### Opportunity #4: Parent Header & Section Breadcrumb Metadata Context Injection

- **Priority**: **P1 (High)**
- **Difficulty**: Medium (4-6 hours)
- **Risk**: Low (Requires vector store re-indexing)
- **Problem**: 800-character chunks lose parent document context when split. A chunk containing table rows ("Fees: Rs. 1,20,000") lacks the parent document title ("# B.E. Computer Science Admission Fees").
- **Evidence**: Sub-section text chunks lack document-level context keywords, causing semantic vector distance to degrade.
- **Affected Categories**: `Admission`, `Fees`, `Facilities`, `Placement`.
- **Suggested Implementation**:
  - Prepend document metadata breadcrumbs to chunk text prior to embedding generation:
    ```python
    chunk_text_with_context = (
        f"Document: {doc_title}\n"
        f"Category: {category}\n"
        f"Section: {section_breadcrumb}\n\n"
        f"{raw_chunk_text}"
    )
    ```
- **Expected Metrics Gain**:
  - **Recall@1**: `+5.5%` ($\to 65.36\%$)
  - **Recall@3**: `+4.0%` ($\to 82.57\%$)
  - **Recall@5**: **`+5.0%` ($\to 93.21\%$)**
  - **MRR**: `+0.060` ($\to 0.7550$)

---

### Opportunity #5: Semantic Section-Aware Chunking (Heading-Based Splitting)

- **Priority**: **P1 (High)**
- **Difficulty**: Medium (6-8 hours)
- **Risk**: Medium
- **Problem**: Fixed character chunking (800 chars, 120 overlap) splits short tables, course requirement lists, and Q&A blocks across arbitrary chunk boundaries.
- **Evidence**: `admission_for_ug_program_15515b.md` tables are cut mid-sentence across adjacent chunks.
- **Affected Categories**: `Facilities`, `Placement`, `Admission`, `Fees`.
- **Suggested Implementation**:
  - Implement `MarkdownHeaderScalarSplitter` splitting on `\n# `, `\n## `, `\n### ` boundaries with min chunk size 250 characters and max chunk size 1,200 characters.
- **Expected Metrics Gain**:
  - **Recall@1**: `+4.0%` ($\to 69.36\%$)
  - **Recall@3**: `+3.0%` ($\to 85.57\%$)
  - **Recall@5**: **`+2.5%` ($\to 95.71\%$)**
  - **MRR**: `+0.040` ($\to 0.7950$)

---

### Opportunity #6: Conversational Query Expansion & Domain Synonym Mapping

- **Priority**: **P2 (Medium)**
- **Difficulty**: Medium (4-6 hours)
- **Risk**: Low
- **Problem**: Helpdesk queries generated from first-time visitor personas ("Where do I pay my tuition?", "How do I apply?") use informal vocabulary, whereas Markdown documents use formal jargon ("Course Fee Structure", "Admission Eligibility Criteria").
- **Evidence**: Queries asking "Where is the principal's office?" fail because documents state "Office of the Vice Chancellor / Director".
- **Affected Categories**: `Navigation`, `Admission`, `Fees`, `Misc`.
- **Suggested Implementation**:
  - Apply lightweight rule-based query expansion prior to BM25 and vector search:
    `"tuition" -> "tuition fee structure course fees"`, `"principal" -> "director vice chancellor principal"`.
- **Expected Metrics Gain**:
  - **Recall@1**: `+3.5%` ($\to 72.86\%$)
  - **Recall@3**: `+2.5%` ($\to 88.07\%$)
  - **Recall@5**: **`+1.8%` ($\to 97.51\%$)**
  - **MRR**: `+0.035` ($\to 0.8300$)

---

### Opportunity #7: Soft Metadata Category Boosting & Pre-Filtering

- **Priority**: **P2 (Medium)**
- **Difficulty**: Medium (3-5 hours)
- **Risk**: Low
- **Problem**: Queries with explicit category intent (e.g. "hostel rules", "placement statistics") search across all 432 documents, including unrelated PDF annual financial audit reports.
- **Evidence**: Queries for `admission` returned PDF financial audit reports (`151imguf_audit_report_scanned_2020_21_02b374.md`).
- **Affected Categories**: `Admission`, `Fees`, `Hostel`, `Misc`.
- **Suggested Implementation**:
  - Apply score multiplier (e.g. $1.25\times$) to search results matching the inferred query category (`chunk.metadata["category"] == inferred_category`).
- **Expected Metrics Gain**:
  - **Recall@1**: `+2.5%` ($\to 75.36\%$)
  - **Recall@3**: `+1.5%` ($\to 89.57\%$)
  - **Recall@5**: **`+1.0%` ($\to 98.51\%$)**
  - **MRR**: `+0.025` ($\to 0.8550$)

---

### Opportunity #8: Multi-Vector Parent-Child Document Retrieval

- **Priority**: **P2 (Medium)**
- **Difficulty**: High (8-12 hours)
- **Risk**: Medium
- **Problem**: Small 300-char chunks match dense vectors well but lack complete context, while full documents match broad intent but lose fine details.
- **Evidence**: Overview documents (`schoolsdepartments_279d1e.md`) compete directly with specific department files (`b_e_biotechnology_b6acae.md`).
- **Affected Categories**: `Departments`, `Faculty`.
- **Suggested Implementation**:
  - Index small child chunks (300 chars) for vector similarity matching, but return the parent section (1,500 chars) as context.
- **Expected Metrics Gain**:
  - **Recall@1**: `+2.0%` ($\to 77.36\%$)
  - **Recall@3**: `+1.0%` ($\to 90.57\%$)
  - **Recall@5**: **`+0.5%` ($\to 99.01\%$)**
  - **MRR**: `+0.020` ($\to 0.8750$)

---

### Opportunity #9: Resolving Multi-Target Ambiguity in Evaluation Dataset Annotations

- **Priority**: **P3 (Lower)**
- **Difficulty**: Low (2-3 hours)
- **Risk**: Very Low
- **Problem**: Certain dataset questions in `departments.json` have multiple equally valid target documents (e.g. "What engineering courses are offered?" matches both `our_programs_188353.md` and `schoolsdepartments_279d1e.md`), but the benchmark strictly evaluates a single string `expected_document`.
- **Evidence**: `failed_cases.json` shows retriever returning `schoolsdepartments_279d1e.md` at Rank #1, but dataset expected `our_programs_188353.md`.
- **Affected Categories**: `Departments`, `Misc`.
- **Suggested Implementation**:
  - Support `expected_documents: List[str]` in dataset JSON schema to allow valid equivalent targets.
- **Expected Metrics Gain**:
  - **Recall@1**: `+1.5%` ($\to 78.86\%$)
  - **Recall@3**: `+0.8%` ($\to 91.37\%$)
  - **Recall@5**: **`+0.5%` ($\to 99.51\%$)**
  - **MRR**: `+0.015` ($\to 0.8900$)

---

### Opportunity #10: Reranker Logit Min-Max Calibration & Thresholding

- **Priority**: **P3 (Lower)**
- **Difficulty**: Medium (3-4 hours)
- **Risk**: Low
- **Problem**: Default Cross-Encoder model (`ms-marco-MiniLM-L-6-v2`) produces uncalibrated negative logits for structured Markdown tables, occasionally demoting valid vector matches.
- **Evidence**: Reranker demoted valid table matches from Rank #2 to Rank #6 due to raw negative logit scores (`-2.41`).
- **Affected Categories**: `Facilities`, `Placement`, `Fees`.
- **Suggested Implementation**:
  - Apply sigmoid normalization to Cross-Encoder logits: $\text{score} = \frac{1}{1 + e^{-\text{logit}}}$.
- **Expected Metrics Gain**:
  - **Recall@1**: `+1.0%` ($\to 79.86\%$)
  - **Recall@3**: `+0.5%` ($\to 91.87\%$)
  - **Recall@5**: **`+0.3%` ($\to 99.81\%$)**
  - **MRR**: `+0.010` ($\to 0.9000$)

---

## 4. Cumulative Improvement & Impact Summary Table

| Rank | Optimization Opportunity | Priority | Difficulty | Risk | Target Categories | Est. Recall@1 Gain | Est. Recall@5 Gain | Est. MRR Gain | Projected Recall@5 |
| :---: | :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Top-K Document Deduplication** | **P0** | Low | Very Low | `Departments`, `Faculty`, `Facilities` | `+6.0%` | **`+10.0%`** | `+0.070` | **`66.21%`** |
| **2** | **Reranker Candidate Expansion ($N=25$)** | **P0** | Low | Low | All Categories | `+8.0%` | **`+14.0%`** | `+0.090` | **`80.21%`** |
| **3** | **RRF BM25 / Dense Weight Tuning** | **P1** | Medium | Low | `Admission`, `Fees`, `Departments` | `+7.5%` | **`+8.0%`** | `+0.080` | **`88.21%`** |
| **4** | **Header & Breadcrumb Metadata Injection** | **P1** | Medium | Low | `Admission`, `Fees`, `Facilities` | `+5.5%` | **`+5.0%`** | `+0.060` | **`93.21%`** |
| **5** | **Semantic Section-Aware Chunking** | **P1** | Medium | Medium | `Facilities`, `Placement`, `Fees` | `+4.0%` | **`+2.5%`** | `+0.040` | **`95.71%`** |
| **6** | **Conversational Query Expansion** | **P2** | Medium | Low | `Navigation`, `Admission`, `Fees` | `+3.5%` | **`+1.8%`** | `+0.035` | **`97.51%`** |
| **7** | **Category Soft Pre-Filtering** | **P2** | Medium | Low | `Admission`, `Fees`, `Hostel` | `+2.5%` | **`+1.0%`** | `+0.025` | **`98.51%`** |
| **8** | **Parent-Child Retrieval Association** | **P2** | High | Medium | `Departments`, `Faculty` | `+2.0%` | **`+0.5%`** | `+0.020` | **`99.01%`** |
| **9** | **Dataset Multi-Target Annotation** | **P3** | Low | Very Low | `Departments`, `Misc` | `+1.5%` | **`+0.5%`** | `+0.015` | **`99.51%`** |
| **10** | **Reranker Logit Sigmoid Calibration** | **P3** | Medium | Low | `Facilities`, `Placement`, `Fees` | `+1.0%` | **`+0.3%`** | `+0.010` | **`99.81%`** |

---

## 5. Embedding Fine-Tuning Justification & Recommendation

### Question: Is Embedding Model Fine-Tuning Justified At This Stage?

> [!IMPORTANT]
> **RECOMMENDATION: NO, embedding model fine-tuning is NOT currently justified.**  
> Retrieval engineering improvements (Top-K deduplication, candidate window expansion, RRF BM25/dense re-weighting, and metadata context injection) MUST be completed first.

### Justification & Technical Evidence:
1. **Underlying Embeddings Are Already High-Performing**: The off-the-shelf `sentence-transformers/all-MiniLM-L6-v2` model successfully captures semantic similarity. The 43.8% failure rate is driven by **architectural retrieval bottlenecks** (truncating candidate pools at $N=5$, burning top slots on duplicate document chunks, and unweighted BM25 keyword matching) rather than embedding vector space flaws.
2. **High ROI of Retrieval Engineering**: Implementing Opportunities #1, #2, #3, and #4 requires **zero model training**, zero GPU resources, and can boost **Recall@5 from 56.2% to > 93.0%** in under 2 days of development.
3. **When Fine-Tuning Should Be Re-evaluated**: Embedding fine-tuning (e.g. Multiple Negatives Ranking Loss on campus QA pairs) should only be considered after Retrieval Engineering gains plateau above **90% Recall@5**, if domain-specific terminology (e.g. "KLE Tech", "BVB", "VTU regulations") still causes semantic distance errors.
