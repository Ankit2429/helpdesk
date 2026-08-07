"""
inspect_dep001.py - Checks what the KB actually says about CSE specializations,
what was retrieved, and what the LLM generated.
"""
import json
from pathlib import Path

data = json.load(open("evaluation/results/baseline_vs_optimized_comparison.json"))
for item in data:
    if item["id"] == "DEP001":
        opt = item["optimized"]
        print("=== DEP001 ===")
        print(f"Question : {item['question']}")
        print(f"Sources  : {opt['sources']}")
        print(f"Reply    : {opt['reply']}")
        print(f"is_correct={opt['is_correct']} | hallucination={opt['hallucination']}")
