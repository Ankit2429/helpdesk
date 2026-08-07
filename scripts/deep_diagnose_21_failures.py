"""
deep_diagnose_21_failures.py
Performs deep root cause classification for each of the 21 failed benchmark questions.
"""

import json
import yaml
import re
from pathlib import Path

def main():
    json_path = Path("evaluation/results/baseline_vs_optimized_comparison.json")
    if not json_path.exists():
        print("Comparison JSON not found!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Load original questions yaml
    q_file = Path("evaluation/questions.yaml")
    yaml_questions = {}
    if q_file.exists():
        with open(q_file, "r", encoding="utf-8") as f:
            ydata = yaml.safe_load(f)
            for q in ydata.get("questions", []):
                yaml_questions[q["id"]] = q

    campus_guide = Path("data/knowledge/campus_guide.txt").read_text(encoding="utf-8") if Path("data/knowledge/campus_guide.txt").exists() else ""

    print("=" * 100)
    print("      DEEP ROOT CAUSE DIAGNOSTIC OF ALL FAILED BENCHMARK QUESTIONS")
    print("=" * 100)

    for item in data:
        qid = item["id"]
        opt = item["optimized"]
        base = item["baseline"]
        
        # We look at questions marked FAIL in optimized
        if not opt["is_correct"]:
            y_info = yaml_questions.get(qid, {})
            qtext = item["question"]
            exp_kws = y_info.get("expected_answer_keywords", item.get("expected_keywords", []))
            exp_srcs = y_info.get("expected_sources", [])
            reply = opt["reply"]
            retrieved_srcs = opt["sources"]
            
            # Check if info is in campus_guide.txt
            in_campus_guide = False
            cg_keywords = []
            for kw in exp_kws:
                if str(kw).lower() in campus_guide.lower():
                    cg_keywords.append(str(kw))
            if len(cg_keywords) > 0:
                in_campus_guide = True
                
            print(f"\nID: [{qid}] | Category: {item['category']}")
            print(f"Question: \"{qtext}\"")
            print(f"Expected Keywords: {exp_kws}")
            print(f"Retrieved Sources: {retrieved_srcs}")
            print(f"Generated Reply  : \"{reply[:180]}...\"" if len(reply) > 180 else f"Generated Reply  : \"{reply}\"")
            print(f"Found in campus_guide.txt? : {in_campus_guide} ({cg_keywords})")
            print("-" * 100)

if __name__ == "__main__":
    main()
