# Campus Helpdesk Robot RAG Evaluation Summary Report

**Timestamp**: 2026-07-28T09:53:27Z  
**Total Benchmark Questions**: 25  
**Overall RAG Quality Score**: **73.39%**  
**Average Retrieval Latency**: 292.6 ms  

## Aggregate Metric Overview

| Metric | Score |
|---|---|
| **Overall RAG Quality Score** | **73.39%** |
| **Recall@5** | 80.00% |
| **Recall@10** | 90.00% |
| **Mean Reciprocal Rank (MRR)** | 0.6217 |
| **Keyword Coverage** | 78.00% |

## Per-Category Accuracy Breakdown

| Category | Questions | Recall@5 | Recall@10 | MRR | Keyword Coverage | Category Accuracy |
|---|---|---|---|---|---|---|
| **Library** | 4 | 100.00% | 100.00% | 1.0000 | 58.33% | **86.11%** |
| **Admissions** | 4 | 50.00% | 87.50% | 0.4524 | 62.50% | **52.58%** |
| **Departments** | 4 | 100.00% | 100.00% | 0.5417 | 100.00% | **84.72%** |
| **Placements** | 4 | 100.00% | 100.00% | 1.0000 | 100.00% | **100.0%** |
| **Hostel** | 4 | 50.00% | 75.00% | 0.2917 | 41.67% | **40.28%** |
| **Academics** | 5 | 80.00% | 80.00% | 0.4800 | 100.00% | **76.0%** |

## Question-Level Diagnostics

| ID | Category | Question | Recall@5 | MRR | KW Coverage | Latency |
|---|---|---|---|---|---|---|
| `LIB001` | Library | Where is the Central Library located?... | 1.0 | 1.0 | 0.00% | 440.94ms |
| `LIB002` | Library | What is the carpet area and seating capacity ... | 1.0 | 1.0 | 100.00% | 292.12ms |
| `LIB003` | Library | How many digital ebooks are available in the ... | 1.0 | 1.0 | 100.00% | 265.59ms |
| `LIB004` | Library | What online database subscriptions are provid... | 1.0 | 1.0 | 33.33% | 268.28ms |
| `ADM001` | Admissions | What entrance exams are accepted for B.E. und... | 0.0 | 0.1667 | 0.00% | 427.64ms |
| `ADM002` | Admissions | What is the official Karnataka CET portal web... | 1.0 | 1.0 | 100.00% | 357.71ms |
| `ADM003` | Admissions | What is the minimum eligibility percentage fo... | 0.0 | 0.1429 | 100.00% | 326.84ms |
| `ADM004` | Admissions | How do candidates apply under the Management ... | 1.0 | 0.5 | 50.00% | 282.64ms |
| `DEP001` | Departments | What specialization streams are offered under... | 1.0 | 0.3333 | 100.00% | 264.08ms |
| `DEP002` | Departments | What degree programs are offered by the Schoo... | 1.0 | 1.0 | 100.00% | 266.18ms |
| `DEP003` | Departments | Which department manages research inVLSI, pow... | 1.0 | 0.5 | 100.00% | 218.92ms |
| `DEP004` | Departments | What specialized postgraduate law program is ... | 1.0 | 0.3333 | 100.00% | 314.07ms |
| `PLC001` | Placements | What resources and assistance are provided by... | 1.0 | 1.0 | 100.00% | 160.68ms |
| `PLC002` | Placements | Which global education partner collaborates f... | 1.0 | 1.0 | 100.00% | 315.94ms |
| `PLC003` | Placements | What companies and industries hire graduates ... | 1.0 | 1.0 | 100.00% | 285.85ms |
| `PLC004` | Placements | How are placement records and brochures made ... | 1.0 | 1.0 | 100.00% | 213.01ms |
| `HST001` | Hostel | What residential facilities and accommodation... | 1.0 | 0.5 | 33.33% | 256.88ms |
| `HST002` | Hostel | What sports and fitness amenities are located... | 1.0 | 0.5 | 33.33% | 301.52ms |
| `HST003` | Hostel | What medical and health emergency services ar... | 0.0 | 0.1667 | 66.67% | 289.63ms |
| `HST004` | Hostel | What food and dining options exist in campus ... | 0.0 | 0.0 | 33.33% | 228.29ms |
| `ACA001` | Academics | What research facilities and specialized labs... | 1.0 | 1.0 | 100.00% | 276.3ms |
| `ACA002` | Academics | What is the duration and structure of the Ph.... | 1.0 | 1.0 | 100.00% | 350.09ms |
| `ACA003` | Academics | How are continuous internal evaluations (CIE)... | 0.0 | 0.0 | 100.00% | 309.53ms |
| `ACA004` | Academics | What undergraduate degree is offered in Hotel... | 1.0 | 0.2 | 100.00% | 296.29ms |
| `ACA005` | Academics | What undergraduate program is offered in Comp... | 1.0 | 0.2 | 100.00% | 305.92ms |