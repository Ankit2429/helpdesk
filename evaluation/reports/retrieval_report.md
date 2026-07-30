# RAG Vector & Hybrid Retrieval Benchmark Report

- **Timestamp**: `2026-07-29T12:02:55Z`
- **Total Benchmark Queries**: `1014`
- **Overall Success Rate (Top-5 Match)**: `65.29%`
- **Overall Mean Reciprocal Rank (MRR)**: `0.5265`
- **P95 Retrieval Latency**: `7002.12 ms`

## Executive Summary Metrics

| Metric | Score | Production Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Recall@1** | `43.49%` | `>= 80.0%` | **NEEDS OPTIMIZATION** |
| **Recall@3** | `61.34%` | `>= 85.0%` | **NEEDS OPTIMIZATION** |
| **Recall@5** | `65.29%` | `>= 90.0%` | **NEEDS OPTIMIZATION** |
| **Mean Reciprocal Rank (MRR)** | `0.5265` | `>= 0.8500` | **NEEDS OPTIMIZATION** |
| **Success Rate** | `65.29%` | `>= 90.0%` | **NEEDS OPTIMIZATION** |
| **Failure Rate** | `34.71%` | `<= 10.0%` | - |
| **Mean Latency** | `5478.69 ms` | `<= 50.0 ms` | - |
| **Median Latency** | `5346.96 ms` | `<= 30.0 ms` | - |
| **P95 Latency** | `7002.12 ms` | `<= 100.0 ms` | **NEEDS OPTIMIZATION** |

## Retrieval Visualizations

![Recall by Category](file:///d:/AUNTII/evaluation/reports/plots/recall_by_category.png)
![Overall Accuracy](file:///d:/AUNTII/evaluation/reports/plots/overall_accuracy.png)
![Latency Distribution](file:///d:/AUNTII/evaluation/reports/plots/latency_distribution.png)
![Failure Count by Category](file:///d:/AUNTII/evaluation/reports/plots/failure_count_by_category.png)

## Domain Category Performance Breakdown

| Category | Total Queries | Success Rate | Recall@1 | Recall@3 | Recall@5 | MRR | Mean Latency | P95 Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Admission** | 5 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0000 | 10494.93 ms | 13221.41 ms |
| **Departments** | 843 | 64.8% | 41.3% | 60.5% | 64.8% | 0.5119 | 5461.50 ms | 7051.43 ms |
| **Facilities** | 45 | 75.6% | 60.0% | 73.3% | 75.6% | 0.6711 | 5410.30 ms | 6323.92 ms |
| **Faculty** | 76 | 76.3% | 63.2% | 75.0% | 76.3% | 0.6846 | 5554.99 ms | 6599.06 ms |
| **Fees** | 5 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0000 | 5145.69 ms | 5416.47 ms |
| **Misc** | 6 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0000 | 5320.63 ms | 5987.67 ms |
| **Navigation** | 29 | 79.3% | 62.1% | 75.9% | 79.3% | 0.6868 | 5367.98 ms | 5863.56 ms |
| **Placement** | 5 | 20.0% | 0.0% | 0.0% | 20.0% | 0.0400 | 3980.85 ms | 4533.54 ms |

## Failure Analysis Summary

- **Total Failed Retrievals**: `352` items

| ID | Category | Question | Expected Document | Diagnosed Failure Reason |
| :---: | :--- | :--- | :--- | :--- |
| 1 | Admission | How do I get admission here? | `203imguf_call_for_admission_mse_2024_25_15878c.md` | Expected document '203imguf_call_for_admission_mse_2024_25_15878c.md' not found in top 5 retrieved results |
| 2 | Admission | Where is the admission office? | `203imguf_call_for_admission_mse_2024_25_15878c.md` | Expected document '203imguf_call_for_admission_mse_2024_25_15878c.md' not found in top 5 retrieved results |
| 3 | Admission | Which documents should I bring for ad... | `203imguf_call_for_admission_mse_2024_25_15878c.md` | Expected document '203imguf_call_for_admission_mse_2024_25_15878c.md' not found in top 5 retrieved results |
| 4 | Admission | Can I get admission through KCET? | `203imguf_call_for_admission_mse_2024_25_15878c.md` | Expected document '203imguf_call_for_admission_mse_2024_25_15878c.md' not found in top 5 retrieved results |
| 5 | Admission | What is the admission process? | `203imguf_call_for_admission_mse_2024_25_15878c.md` | Expected document '203imguf_call_for_admission_mse_2024_25_15878c.md' not found in top 5 retrieved results |
| 2 | Departments | Does this college have a department f... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 3 | Departments | Can I meet a faculty member from Abou... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 5 | Departments | Where is the Industry Supported Labs ... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 6 | Departments | Can I meet a faculty member from Our ... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 7 | Departments | Which block is Programs Offered in? | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 8 | Departments | Can I meet a faculty member from Bran... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 9 | Departments | Does this college have a department f... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 10 | Departments | Where is the Branches Offered departm... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 11 | Departments | Does this college have a department f... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 13 | Departments | What courses are offered in Universit... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 15 | Departments | Does this college have a department f... | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 17 | Departments | Which block is Companies Provide in? | `19krf_about_kle_technological_universityhubba_1bddac.md` | Expected document '19krf_about_kle_technological_universityhubba_1bddac.md' not found in top 5 retrieved results |
| 22 | Departments | Does this college have a department f... | `20rkf_about_kle_technological_universityhubba_6fa2a0.md` | Expected document '20rkf_about_kle_technological_universityhubba_6fa2a0.md' not found in top 5 retrieved results |
| 24 | Departments | Which block is THANK YOU in? | `20rkf_about_kle_technological_universityhubba_6fa2a0.md` | Expected document '20rkf_about_kle_technological_universityhubba_6fa2a0.md' not found in top 5 retrieved results |
| 25 | Departments | Can I meet a faculty member from Comp... | `20rkf_about_kle_technological_universityhubba_6fa2a0.md` | Expected document '20rkf_about_kle_technological_universityhubba_6fa2a0.md' not found in top 5 retrieved results |
| 26 | Departments | Does this college have a department f... | `20rkf_about_kle_technological_universityhubba_6fa2a0.md` | Expected document '20rkf_about_kle_technological_universityhubba_6fa2a0.md' not found in top 5 retrieved results |
| 27 | Departments | What courses are offered in Industry ... | `20rkf_about_kle_technological_universityhubba_6fa2a0.md` | Expected document '20rkf_about_kle_technological_universityhubba_6fa2a0.md' not found in top 5 retrieved results |
| 32 | Departments | Where is the Certifications department? | `21rkf_about_kle_technological_universityhubba_073ae5.md` | Expected document '21rkf_about_kle_technological_universityhubba_073ae5.md' not found in top 5 retrieved results |
| 34 | Departments | Where is the Companies Provide depart... | `21rkf_about_kle_technological_universityhubba_073ae5.md` | Expected document '21rkf_about_kle_technological_universityhubba_073ae5.md' not found in top 5 retrieved results |
| 38 | Departments | Does this college have a department f... | `about_hubballi_campus_b5a07d.md` | Expected document 'about_hubballi_campus_b5a07d.md' not found in top 5 retrieved results |

*...and 327 more. Full failure traces saved to `evaluation/reports/failed_cases.json`.*

## How to Interpret Metrics & Decide Next Steps

### Metric Definitions & Target Benchmarks
1. **Recall@1 (Target: >= 80%)**:
   - *Meaning*: The exact target document is returned as the #1 top-ranked search result.
   - *Decision Rule*: If Recall@1 < 80%, the retriever needs stronger term re-weighting (e.g. BM25 tuning or cross-encoder reranking).

2. **Recall@3 & Recall@5 (Target: >= 90%)**:
   - *Meaning*: The target document is included within the top 3 or top 5 search context blocks.
   - *Decision Rule*: If Recall@5 < 90%, embedding chunk size or vector index coverage is inadequate and requires re-indexing.

3. **Mean Reciprocal Rank (MRR) (Target: >= 0.8500)**:
   - *Meaning*: Evaluates average position rank quality ($1/\text{rank}$). A score of 1.0 means perfect #1 ranking.
   - *Decision Rule*: If MRR < 0.85, search result ordering is sub-optimal.

4. **P95 Latency (Target: <= 100 ms)**:
   - *Meaning*: 95% of helpdesk queries retrieve results in under 100 ms.
   - *Decision Rule*: If P95 Latency > 100 ms, optimize vector search index (FAISS HNSW or IVF index quantization).