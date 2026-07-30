import os
import json
import uuid
import time
import yaml
from typing import List, Dict, Any

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_PATH = os.path.join(BASE_DIR, "datasets", "real_world.yaml")
RESULTS_PATH = os.path.join(BASE_DIR, "results", "real_world_results.jsonl")

# Ensure results directory exists
os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)

# Import the production chat service (do not modify its behavior)
# Adjust import according to actual project structure
from src.campus_helpdesk.application.rag_chat_service import RAGChatService


def load_dataset() -> Dict[str, List[Dict[str, Any]]]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def simple_accuracy(answer: str, reference: str) -> bool:
    """Very lightweight string similarity check.
    Returns True if the answer contains the reference (case‑insensitive) or
    the similarity ratio exceeds 0.8.
    """
    if not reference:
        return True  # No reference provided → cannot judge
    low_ans = answer.lower()
    low_ref = reference.lower()
    if low_ref in low_ans:
        return True
    # fallback to ratio
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, low_ans, low_ref).ratio()
    return ratio >= 0.8


def run_conversation(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a multi‑turn conversation using RAGChatService.
    Returns a list of per‑turn result dictionaries.
    """
    service = RAGChatService()
    session_id = str(uuid.uuid4())
    turn_results = []
    for turn_text in conversation["turns"]:
        start = time.time()
        # The service method name may differ; adjust if needed.
        chat_result = service.respond(user_query=turn_text, session_id=session_id)
        latency_ms = (time.time() - start) * 1000
        # Extract fields from ChatResult (assumed attributes)
        answer = getattr(chat_result, "answer", "")
        citations = getattr(chat_result, "citations", [])
        confidence = getattr(chat_result, "confidence_score", 0.0)
        hallucination_risk = getattr(chat_result, "hallucination_risk", "Low")
        # Record
        turn_record = {
            "conversation_id": conversation["id"],
            "session_id": session_id,
            "turn_index": len(turn_results),
            "user_query": turn_text,
            "answer": answer,
            "citations": citations,
            "confidence_score": confidence,
            "hallucination_risk": hallucination_risk,
            "latency_ms": latency_ms,
            "expected_answer": conversation.get("expected_answer", ""),
            "expected_citations": conversation.get("expected_citations", []),
            "answer_correct": simple_accuracy(answer, conversation.get("expected_answer", "")),
        }
        turn_results.append(turn_record)
    return turn_results


def main():
    dataset = load_dataset()
    all_results = []
    for category, conv_list in dataset.items():
        for conv in conv_list:
            turn_results = run_conversation(conv)
            all_results.extend(turn_results)
    # Write JSON lines
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for rec in all_results:
            f.write(json.dumps(rec) + "\n")
    print(f"Real‑world evaluation completed. Results written to {RESULTS_PATH}")

if __name__ == "__main__":
    main()
