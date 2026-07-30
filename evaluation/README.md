# RAG Evaluation Framework

A modular, lightweight, and decoupled benchmarking suite designed specifically for evaluating Retrieval-Augmented Generation (RAG) performance in the **Campus Helpdesk Robot** project.

---

## 🎯 Purpose & Objectives

The RAG Evaluation Framework exists to provide a rigorous, repeatable, and scientific benchmark for testing search and generation performance across various campus domains without modifying any production application or runtime code.

Key objectives include:
- **Retrieval Precision & Recall Measurement**: Evaluate vector/hybrid search performance (`Precision@K`, `Recall@K`, `MRR`, `NDCG@K`, `Hit Rate`).
- **Response Quality Benchmarking**: Quantify output accuracy against ground-truth answers using Exact Match and Token-Level F1 metrics.
- **Regression Detection**: Catch retrieval degradation early when embedding models, chunking strategies, or reranking algorithms are changed.
- **Category-Wise Performance Analysis**: Identify specific domain weaknesses (e.g., fee structure questions vs campus navigation queries).

---

## 📁 Directory Architecture

```
evaluation/
├── datasets/             # Domain-specific ground-truth test datasets (JSON format)
│   ├── admission.json
│   ├── departments.json
│   ├── hostel.json
│   ├── fees.json
│   ├── placement.json
│   ├── navigation.json
│   ├── facilities.json
│   ├── faculty.json
│   └── misc.json
├── benchmarks/           # Core evaluation metrics, evaluator engine, and CLI entry point
│   ├── benchmark.py       # Main CLI executable runner
│   ├── evaluator.py       # Benchmark evaluation orchestration engine
│   ├── metrics.py         # Pure statistical IR & generation metrics algorithms
│   └── report_generator.py # Markdown, JSON, and terminal report formatters
├── reports/              # Destination directory for generated evaluation reports
│   └── .gitkeep
└── README.md             # Comprehensive framework documentation
```

---

## 📝 Dataset JSON Schema

Each category dataset in `evaluation/datasets/*.json` contains a list of JSON records structured as follows:

```json
[
  {
    "id": 1,
    "question": "What is the fee structure for B.E. Computer Science admissions?",
    "expected_document": "fees_structure_2024.md",
    "expected_answer": "The annual tuition fee for B.E. Computer Science is INR 1,25,000.",
    "category": "Fees",
    "expected_chunks": [
      "fee_chunk_102",
      "fee_chunk_103"
    ],
    "metadata": {
      "academic_year": "2024-25",
      "source_url": "https://www.kletech.ac.in/fees"
    },
    "difficulty": "medium",
    "keywords": [
      "fee",
      "tuition",
      "computer science",
      "B.E."
    ],
    "synonyms": [
      "cost",
      "pricing",
      "charges"
    ]
  }
]
```

### Schema Field Specification

| Field Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `id` | `integer` or `string` | **Yes** | Unique identifier within the dataset file. |
| `question` | `string` | **Yes** | The user query text to test against the RAG system. |
| `expected_document` | `string` | **Yes** | Identifier, filename, or unique title of the expected source document. |
| `expected_answer` | `string` | **Yes** | Canonical reference ground-truth answer string. |
| `category` | `string` | **Yes** | Domain category (e.g., `Admission`, `Hostel`, `Fees`, `Placement`). |
| `expected_chunks` | `list[string]` | Optional | Specific vector chunk IDs expected in retrieval context. |
| `metadata` | `object` | Optional | Custom context metadata (URLs, dates, target personas). |
| `difficulty` | `string` | Optional | Complexity level: `"easy"`, `"medium"`, `"hard"`. |
| `keywords` | `list[string]` | Optional | Key terms expected to appear in query or retrieved context. |
| `synonyms` | `list[string]` | Optional | Query term variations for testing query rewriters. |

---

## ➕ How to Add New Benchmark Questions

1. Identify the appropriate domain category file inside `evaluation/datasets/` (e.g. `evaluation/datasets/hostel.json`).
2. Add a new JSON record following the schema format above.
3. Ensure `id` is unique within that file.
4. Specify a clear, unambiguous `expected_document` and `expected_answer`.
5. Save the JSON file and validate formatting by running a dry-run benchmark:

```bash
python evaluation/benchmarks/benchmark.py --dry-run
```

---

## 📊 Benchmark Metrics Explained

### Retrieval Metrics
- **Precision@K (`P@K`)**: Proportion of retrieved documents in the top-$K$ results that match the expected document reference.
- **Recall@K (`R@K`)**: Proportion of expected target documents retrieved within the top-$K$ results.
- **Mean Reciprocal Rank (`MRR`)**: The multiplicative inverse of the rank position of the first matching document ($1/\text{rank}$).
- **Hit Rate@K (`HR@K`)**: Binary indicator ($1.0$ or $0.0$) evaluating whether at least one target document appears in top-$K$.
- **NDCG@K**: Normalized Discounted Cumulative Gain penalizing target documents retrieved at lower positions in the rank list.

### Generation Metrics
- **Exact Match (`EM`)**: String equality score ($1.0$ or $0.0$) after lowercasing, punctuation stripping, and whitespace normalization.
- **Token F1 (`F1`)**: Harmonic mean of token-level precision and recall between the generated response and the expected answer.

---

## 🚀 Execution & Command Line Usage

### Standard Benchmark Run

Run the full benchmark suite across all dataset files:

```bash
python evaluation/benchmarks/benchmark.py
```

### Dry-Run Mode (Mock Execution)

Test dataset loading and report generation without invoking external services:

```bash
python evaluation/benchmarks/benchmark.py --dry-run
```

### Filter by Domain Category

Execute evaluation only for a specific category (e.g., `Fees` or `Admission`):

```bash
python evaluation/benchmarks/benchmark.py --category Fees
```

### Custom Top-K Rank Cut-Off

Change the retrieval evaluation depth cut-off $K$ (default is 5):

```bash
python evaluation/benchmarks/benchmark.py --top-k 10
```

### Custom Dataset & Output Directories

```bash
python evaluation/benchmarks/benchmark.py --dataset-dir evaluation/datasets --output-dir evaluation/reports --verbose
```

---

## 📑 Reports & Output Formats

Every evaluation run automatically generates two output files in `evaluation/reports/`:

1. **`latest_report.md`**: Human-readable Markdown document containing:
   - Summary statistics tables.
   - Category-by-category breakdown matrix.
   - Per-item query scores and latency measurements.
2. **`latest_report.json`**: Complete structured JSON export containing full raw result dictionaries for programmatic consumption and historical trending.

---

## 🛠️ Guidelines for Future Contributors

1. **Isolation**: Never import code from `evaluation/` into the runtime application (`src/campus_helpdesk` or `bvbcet_rag_pipeline`).
2. **Pluggable Adapters**: When connecting new retrieval pipelines or vector stores, pass a custom wrapper function conforming to `(query: str) -> (list[str], str)` into `RAGEvaluator(rag_pipeline=...)`.
3. **Dataset Quality**: Ensure ground-truth `expected_answer` entries remain clear, concise, and representative of actual verified campus information.
