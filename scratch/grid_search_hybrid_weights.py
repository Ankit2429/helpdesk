"""Fast Grid Search Script for Hybrid RRF Dense/Sparse Weight Combinations."""

import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project root and src to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
src_path = str(Path(__file__).resolve().parent.parent / "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline
from evaluation.benchmarks.retrieval_benchmark import _is_doc_match
from evaluation.benchmarks.retrieval_metrics import calculate_percentile


def fuse_and_rerank(bm25_hits, dense_hits, w_dense, w_sparse, mode, rrf_k, reranker, query, limit=5, dedup=True):
    doc_map = {}
    rrf_scores = {}
    distance_map = {}

    if mode == "dense_only":
        candidates = dense_hits[:25]
    elif mode == "bm25_only":
        candidates = bm25_hits[:25]
    else:
        if w_sparse > 0:
            for rank, match in enumerate(bm25_hits, start=1):
                doc = match.document
                doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
                rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + w_sparse * (1.0 / (rrf_k + rank))
                doc_map[doc_hash] = doc
                distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

        if w_dense > 0:
            for rank, match in enumerate(dense_hits, start=1):
                doc = match.document
                doc_hash = hashlib.sha256(doc.content.strip().encode("utf-8")).hexdigest()
                rrf_scores[doc_hash] = rrf_scores.get(doc_hash, 0.0) + w_dense * (1.0 / (rrf_k + rank))
                doc_map[doc_hash] = doc
                distance_map[doc_hash] = min(distance_map.get(doc_hash, match.distance), match.distance)

        sorted_hashes = sorted(rrf_scores.keys(), key=lambda h: rrf_scores[h], reverse=True)
        from campus_helpdesk.domain.knowledge import SearchResult
        candidates = [SearchResult(document=doc_map[h], distance=distance_map[h]) for h in sorted_hashes[:25]]

    if reranker is not None:
        candidates = reranker.rerank(query, candidates, top_m=25)

    if dedup:
        seen_sources = set()
        deduped = []
        for res in candidates:
            doc = getattr(res, "document", None)
            meta = getattr(doc, "metadata", {}) if doc else {}
            fn = meta.get("source_filename") or meta.get("source") or ""
            if fn not in seen_sources:
                seen_sources.add(fn)
                deduped.append(fn)
                if len(deduped) == limit:
                    break
        return deduped
    else:
        return [getattr(res.document, "metadata", {}).get("source_filename", "") for res in candidates[:limit]]


def run_grid_search():
    # 1. Load Dataset Records
    dataset_dir = Path("evaluation/datasets")
    json_files = sorted(list(dataset_dir.glob("*.json")))
    records = []
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
            records.extend(data)

    print(f"Loaded {len(records)} evaluation records from datasets.")

    # 2. Initialize RAG Components
    settings = Settings(faiss_allow_dangerous_deserialization=True)
    pipeline = create_rag_pipeline(settings)
    hybrid_retriever = pipeline._similarity_store
    reranker = pipeline._reranker

    print("Pre-fetching BM25 and FAISS dense search candidates for all queries...")

    # Pre-fetch candidate hits once
    cached_candidates = []

    def fetch_candidates(item):
        q = item["question"]
        bm25_hits = hybrid_retriever.bm25_store.search(q, limit=25) if hybrid_retriever._bm25_indexed else []
        dense_hits = hybrid_retriever.similarity_store.search(q, limit=25)
        return (item, bm25_hits, dense_hits)

    start_prefetch = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as executor:
        cached_candidates = list(executor.map(fetch_candidates, records))
    print(f"Pre-fetched candidate pools in {round(time.perf_counter() - start_prefetch, 2)}s.")

    weight_combinations = [
        (1.0, 0.0, "dense_only"),
        (0.9, 0.1, "weighted_hybrid"),
        (0.8, 0.2, "weighted_hybrid"),
        (0.7, 0.3, "weighted_hybrid"),
        (0.6, 0.4, "weighted_hybrid"),
        (0.5, 0.5, "weighted_hybrid"),
        (0.4, 0.6, "weighted_hybrid"),
        (0.3, 0.7, "weighted_hybrid"),
        (0.2, 0.8, "weighted_hybrid"),
        (0.1, 0.9, "weighted_hybrid"),
        (0.0, 1.0, "bm25_only"),
    ]

    all_grid_results = []

    for w_dense, w_sparse, mode in weight_combinations:
        start_eval = time.perf_counter()
        r1_hits = 0
        r3_hits = 0
        r5_hits = 0
        mrr_sum = 0.0
        failures = 0
        latencies = []

        for item, bm25_hits, dense_hits in cached_candidates:
            q = item["question"]
            exp = item["expected_document"]

            t0 = time.perf_counter()
            retrieved_docs = fuse_and_rerank(
                bm25_hits, dense_hits, w_dense, w_sparse, mode,
                rrf_k=60, reranker=reranker, query=q, limit=5, dedup=True
            )
            lat = (time.perf_counter() - t0) * 1000
            latencies.append(lat)

            rank = 0
            for idx, doc_name in enumerate(retrieved_docs, start=1):
                if _is_doc_match(doc_name, exp):
                    rank = idx
                    break

            if rank == 1:
                r1_hits += 1
            if 1 <= rank <= 3:
                r3_hits += 1
            if 1 <= rank <= 5:
                r5_hits += 1
            else:
                failures += 1

            if rank > 0:
                mrr_sum += 1.0 / rank

        total = len(records)
        r1_pct = round((r1_hits / total) * 100, 2)
        r3_pct = round((r3_hits / total) * 100, 2)
        r5_pct = round((r5_hits / total) * 100, 2)
        mrr_val = round(mrr_sum / total, 4)
        mean_lat = round(sum(latencies) / total, 2)

        res_row = {
            "weight_dense": w_dense,
            "weight_sparse": w_sparse,
            "fusion_mode": mode,
            "recall_1": r1_pct,
            "recall_3": r3_pct,
            "recall_5": r5_pct,
            "mrr": mrr_val,
            "failed_queries": failures,
            "mean_latency_ms": mean_lat,
        }
        all_grid_results.append(res_row)

        print(f"Weight Combination [Dense: {w_dense:.1f}, Sparse: {w_sparse:.1f}, Mode: {mode:15s}] -> Recall@1: {r1_pct:5.2f}%, Recall@3: {r3_pct:5.2f}%, Recall@5: {r5_pct:5.2f}%, MRR: {mrr_val:.4f}, Failures: {failures:3d}")

    # Sort results descending by Recall@5, then MRR
    all_grid_results.sort(key=lambda r: (r["recall_5"], r["mrr"]), reverse=True)

    output_path = Path("evaluation/reports/hybrid_grid_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_grid_results, f, indent=2)

    best = all_grid_results[0]
    print("\n================ GRID SEARCH SUMMARY ================")
    print(f"BEST CONFIGURATION: Dense={best['weight_dense']}, Sparse={best['weight_sparse']}, Mode={best['fusion_mode']}")
    print(f"Metrics -> Recall@1: {best['recall_1']}%, Recall@3: {best['recall_3']}%, Recall@5: {best['recall_5']}%, MRR: {best['mrr']}")


if __name__ == "__main__":
    run_grid_search()
