"""
export_all_21_failures.py
Dumps full detail of all 21 failed questions into a clean JSON for plan creation.
"""

import json
import yaml
from pathlib import Path

def main():
    json_path = Path("evaluation/results/baseline_vs_optimized_comparison.json")
    if not json_path.exists():
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    q_file = Path("evaluation/questions.yaml")
    yaml_questions = {}
    if q_file.exists():
        with open(q_file, encoding="utf-8") as f:
            ydata = yaml.safe_load(f)
            for q in ydata.get("questions", []):
                yaml_questions[q["id"]] = q

    failed = []
    for item in data:
        qid = item["id"]
        opt = item["optimized"]
        y_info = yaml_questions.get(qid, {})
        
        if not opt["is_correct"]:
            failed.append({
                "id": qid,
                "category": item["category"],
                "question": item["question"],
                "expected_keywords": y_info.get("expected_answer_keywords", item.get("expected_keywords", [])),
                "expected_sources": y_info.get("expected_sources", []),
                "notes": y_info.get("notes", ""),
                "opt_reply": opt["reply"],
                "opt_sources": opt["sources"],
                "opt_conf": opt["confidence_score"],
                "opt_matched_kws": opt["matched_kws"],
                "opt_is_correct": opt["is_correct"],
            })

    with open("evaluation/results/all_21_failures_full.json", "w", encoding="utf-8") as f:
        json.dump(failed, f, indent=2, ensure_ascii=False)
        
    print(f"Dumped {len(failed)} failed questions to evaluation/results/all_21_failures_full.json")

if __name__ == "__main__":
    main()
