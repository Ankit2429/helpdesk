import os
import json
import yaml
import math
from collections import defaultdict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_PATH = os.path.join(BASE_DIR, "results", "real_world_results.jsonl")
METRICS_JSON = os.path.join(BASE_DIR, "results", "real_world_metrics.json")

def expected_answer_match(answer: str, expected: str) -> bool:
    if not expected:
        return True
    low_ans = answer.lower()
    low_exp = expected.lower()
    if low_exp in low_ans:
        return True
    from difflib import SequenceMatcher
    return SequenceMatcher(None, low_ans, low_exp).ratio() >= 0.8

def compute_metrics():
    total_turns = 0
    answer_correct = 0
    citation_correct = 0
    citation_total = 0
    conversation_correct = 0
    memory_correct = 0
    navigation_correct = 0
    navigation_total = 0
    hallucination_hits = 0
    total_latency = 0.0
    confidence_bins = defaultdict(lambda: [0, 0])  # bin -> [num_samples, num_correct]

    # For memory tracking we need to compare repeated queries within same session
    session_history = defaultdict(dict)  # session_id -> {query: answer}

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            total_turns += 1
            total_latency += rec.get("latency_ms", 0)
            # Answer accuracy
            if expected_answer_match(rec.get("answer", ""), rec.get("expected_answer", "")):
                answer_correct += 1
                answer_is_correct = True
            else:
                answer_is_correct = False
            # Citation accuracy
            expected_cits = set(rec.get("expected_citations", []))
            found_cits = set(rec.get("citations", []))
            citation_total += max(1, len(expected_cits))
            if expected_cits and expected_cits.intersection(found_cits):
                citation_correct += 1
            # Conversation accuracy – pronoun resolution heuristic
            pronouns = {"it", "they", "them", "their", "he", "she", "his", "her", "its"}
            if pronouns.intersection(set(rec.get("user_query", "").lower().split())) and answer_is_correct:
                conversation_correct += 1
            # Memory accuracy – same query same session consistency
            sess_id = rec.get("session_id")
            q = rec.get("user_query", "").strip().lower()
            prev = session_history[sess_id].get(q)
            if prev is not None and prev == rec.get("answer"):
                memory_correct += 1
            session_history[sess_id][q] = rec.get("answer")
            # Navigation accuracy – only for category navigation
            if rec.get("category") == "navigation":
                navigation_total += 1
                if answer_is_correct:
                    navigation_correct += 1
            # Hallucination rate
            if rec.get("hallucination_risk", "Low") in ["High", "Very High"]:
                hallucination_hits += 1
            # Confidence calibration bins
            conf = rec.get("confidence_score", 0.0)
            bin_idx = int(conf * 10)
            bin_key = f"{bin_idx * 0.1:.1f}-{(bin_idx + 1) * 0.1:.1f}"
            confidence_bins[bin_key][0] += 1
            confidence_bins[bin_key][1] += int(answer_is_correct)

    metrics = {
        "answer_accuracy": answer_correct / total_turns if total_turns else 0,
        "citation_accuracy": citation_correct / citation_total if citation_total else 0,
        "conversation_accuracy": conversation_correct / total_turns if total_turns else 0,
        "memory_accuracy": memory_correct / total_turns if total_turns else 0,
        "navigation_accuracy": navigation_correct / navigation_total if navigation_total else 0,
        "hallucination_rate": hallucination_hits / total_turns if total_turns else 0,
        "average_latency_ms": total_latency / total_turns if total_turns else 0,
    }
    # Expected Calibration Error (ECE)
    ece = 0.0
    total_samples = 0
    for bin_range, (n, correct) in confidence_bins.items():
        if n == 0:
            continue
        acc = correct / n
        low, high = map(float, bin_range.split("-"))
        midpoint = (low + high) / 2
        ece += abs(acc - midpoint) * n
        total_samples += n
    metrics["confidence_calibration_ece"] = ece / total_samples if total_samples else 0

    os.makedirs(os.path.dirname(METRICS_JSON), exist_ok=True)
    with open(METRICS_JSON, "w", encoding="utf-8") as out:
        json.dump(metrics, out, indent=2)
    print(f"Metrics written to {METRICS_JSON}")

if __name__ == "__main__":
    compute_metrics()
