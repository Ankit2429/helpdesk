"""
Root Cause Classification Script
=================================
Analyzes all failed and partial questions from docs/retrieval_audit_100.json
and classifies them into the 9 user-defined root cause buckets:

1. Missing knowledge base content
2. Incorrect metadata
3. Poor chunking
4. BM25 miss
5. FAISS miss
6. RRF ranking issue
7. Cross-encoder reranking issue
8. Prompt construction issue
9. LLM reasoning issue
"""

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def classify():
    json_path = ROOT_DIR / "docs" / "retrieval_audit_100.json"
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    non_passed = [r for r in results if r["status"] != "PASSED"]

    categories_count = {}
    cause_breakdown = {}

    print(f"Total non-passed items: {len(non_passed)}\n")

    for r in non_passed:
        qid = r["id"]
        cat = r["category"]
        q = r["query"]
        status = r["status"]
        sources = r["sources"]
        conf = r["confidence_score"]
        conf_lvl = r["confidence_level"]
        matched_kws = r["matched_keywords"]
        exp_kws = r["expected_keywords"]

        # Classification logic based on empirical chunk analysis
        # Check source content existence
        source_str = " ".join(sources).lower()

        if "dup" in source_str or "aqar" in source_str or "minutes" in source_str:
            cause = "RRF ranking issue" # duplicate/irrelevant document ranked higher than canonical
        elif conf < 0.50 or not sources or sources == ["unknown"]:
            cause = "Missing knowledge base content"
        elif len(matched_kws) == 0 and conf >= 0.70:
            cause = "Cross-encoder reranking issue" # Reranker chose chunk without expected keywords
        elif len(matched_kws) == 1:
            cause = "Poor chunking" # Information split across multiple chunks
        else:
            cause = "BM25 miss"

        categories_count[cat] = categories_count.get(cat, 0) + 1
        cause_breakdown[cause] = cause_breakdown.get(cause, 0) + 1

        print(f"[{qid}] [{cat:<11}] ({status:<7}) {q[:45]:<45}")
        print(f"   Root Cause: {cause}")
        print(f"   Sources   : {sources[:2]}")
        print(f"   Keywords  : Matched {matched_kws} of Exp {exp_kws}")
        print("-" * 70)

    print("\n=======================================================================")
    print("ROOT CAUSE FREQUENCY BREAKDOWN:")
    print("=======================================================================")
    for cause, count in sorted(cause_breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f" - {cause:<32}: {count} failures")

if __name__ == "__main__":
    classify()
