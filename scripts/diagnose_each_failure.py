"""
diagnose_each_failure.py
Prints detailed per-question diagnosis for all 21 failed benchmark questions.
"""

import json
from pathlib import Path

def main():
    json_path = Path("evaluation/results/failed_questions_analysis.json")
    if not json_path.exists():
        print("Analysis JSON not found!")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        failed_q = json.load(f)

    print(f"Total Failed Questions Analyzed: {len(failed_q)}\n" + "="*90)

    for idx, item in enumerate(failed_q, 1):
        qid = item["id"]
        cat = item["category"]
        qtext = item["question"]
        exp_kws = item["expected_keywords"]
        exp_srcs = item["expected_sources"]
        opt_reply = item["opt_reply"]
        opt_srcs = item["opt_sources"]
        opt_kws = item["opt_matched_kws"]

        print(f"[{idx}/{len(failed_q)}] ID: {qid} | Cat: {cat}")
        print(f"  Question        : \"{qtext}\"")
        print(f"  Expected KWs    : {exp_kws}")
        print(f"  Expected Sources: {exp_srcs}")
        print(f"  Retrieved Srcs  : {opt_srcs}")
        print(f"  Matched KWs     : {opt_kws}")
        print(f"  Generated Answer:\n    \"{opt_reply[:200]}...\"" if len(opt_reply) > 200 else f"  Generated Answer:\n    \"{opt_reply}\"")
        print("-" * 90)

if __name__ == "__main__":
    main()
