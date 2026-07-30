import os
import json
import yaml
from collections import Counter

# Base directories (project root is two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_PATH = os.path.join(BASE_DIR, "results", "real_world_results.jsonl")
SUMMARY_CSV = os.path.join(BASE_DIR, "results", "failure_summary.csv")

# Mapping of internal failure tags to human‑readable categories
CATEGORY_MAP = {
    "retrieval": "Wrong retrieval",
    "rerank": "Wrong reranking",
    "citation": "Wrong citation",
    "hallucination": "Hallucination",
    "confidence": "Low confidence",
    "conversation": "Conversation failure",
    "memory": "Memory failure",
}

# Simple heuristic classifiers – can be extended later
def classify_record(rec: dict) -> list:
    failures = []

    # Retrieval / Citation failures
    if not rec.get("answer_correct", True):
        expected_cits = set(rec.get("expected_citations", []))
        found_cits = set(rec.get("citations", []))
        if expected_cits and not expected_cits.intersection(found_cits):
            failures.append(CATEGORY_MAP["retrieval"])
        else:
            failures.append(CATEGORY_MAP["citation"])

    # Reranking failure – low confidence despite a correct answer
    if rec.get("confidence_score", 0) < 0.4 and rec.get("answer_correct", False):
        failures.append(CATEGORY_MAP["rerank"])

    # Hallucination detection – risk field high/very high
    if rec.get("hallucination_risk", "Low") in ["High", "Very High"]:
        failures.append(CATEGORY_MAP["hallucination"])

    # Low confidence – confidence score below a threshold
    if rec.get("confidence_score", 1) < 0.3:
        failures.append(CATEGORY_MAP["confidence"])

    # Conversation / Pronoun resolution failure
    pronouns = {"it", "they", "them", "their", "he", "she", "his", "her", "its"}
    query_words = set(rec.get("user_query", "").lower().split())
    if pronouns.intersection(query_words) and not rec.get("answer_correct", True):
        failures.append(CATEGORY_MAP["conversation"])

    # Memory failure – repeated question in same session with different answer
    if rec.get("memory_mismatch", False):
        failures.append(CATEGORY_MAP["memory"])

    return failures

def main():
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    counter = Counter()

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            for cat in classify_record(rec):
                counter[cat] += 1

    # Write CSV summary
    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as csvfile:
        csvfile.write("failure_category,count\n")
        for cat, cnt in counter.most_common():
            csvfile.write(f"{cat},{cnt}\n")

    print(f"Failure summary written to {SUMMARY_CSV}")

if __name__ == "__main__":
    main()
