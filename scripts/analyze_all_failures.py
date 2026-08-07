"""
analyze_all_failures.py
Detailed per-question failure diagnostic script.
"""

import json
import yaml
from pathlib import Path

def main():
    json_path = Path("evaluation/results/baseline_vs_optimized_comparison.json")
    if not json_path.exists():
        print("Comparison JSON file not found!")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Load original expected answers/keywords from evaluation/questions.yaml
    questions_yaml_map = {}
    q_file = Path("evaluation/questions.yaml")
    if q_file.exists():
        with open(q_file, encoding="utf-8") as f:
            qdata = yaml.safe_load(f)
            if isinstance(qdata, dict) and "questions" in qdata:
                for q in qdata["questions"]:
                    questions_yaml_map[q["id"]] = q

    failed_questions = []

    for item in data:
        qid = item["id"]
        opt = item["optimized"]
        base = item["baseline"]
        
        # If either baseline or optimized failed, inspect it
        if not opt["is_correct"] or not base["is_correct"]:
            y_info = questions_yaml_map.get(qid, {})
            failed_questions.append({
                "id": qid,
                "category": item["category"],
                "question": item["question"],
                "expected_keywords": y_info.get("expected_answer_keywords", []),
                "expected_sources": y_info.get("expected_sources", []),
                "notes": y_info.get("notes", ""),
                "opt_reply": opt["reply"],
                "opt_sources": opt["sources"],
                "opt_conf": opt["confidence_score"],
                "opt_matched_kws": opt["matched_kws"],
                "opt_is_correct": opt["is_correct"],
                "opt_hallucination": opt["hallucination"],
                "base_reply": base["reply"],
                "base_sources": base["sources"],
                "base_is_correct": base["is_correct"],
            })

    print(f"Found {len(failed_questions)} questions that failed in baseline or optimized evaluation.")
    
    out_path = Path("evaluation/results/failed_questions_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(failed_questions, f, indent=2, ensure_ascii=False)
        
    print(f"Analysis saved to {out_path}")

if __name__ == "__main__":
    main()
