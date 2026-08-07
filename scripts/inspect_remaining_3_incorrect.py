"""
inspect_remaining_3_incorrect.py
Inspects the 3 remaining questions in Category 4 (Hallucination/Incorrect).
"""

import json

def main():
    with open("evaluation/results/audited_4_category_benchmark.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    incorrect = [q for q in data if q["audit_category"] == "4_HALLUCINATION_INCORRECT"]

    print(f"Total Category 4 Incorrect Questions: {len(incorrect)}\n" + "="*90)

    for idx, q in enumerate(incorrect, 1):
        print(f"[{idx}/{len(incorrect)}] ID: {q['id']} | Category: {q['category']}")
        print(f"Question        : \"{q['question']}\"")
        print(f"Expected KWs    : {q['expected_keywords']}")
        print(f"Retrieved Srcs  : {q['sources']}")
        print(f"Generated Reply  : \"{q['reply']}\"")
        print(f"Explanation     : {q['explanation']}")
        print("-" * 90)

if __name__ == "__main__":
    main()
