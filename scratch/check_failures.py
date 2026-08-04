import json

with open("evaluation/results/e2e_qa_log.json", encoding="utf-8") as f:
    d = json.load(f)

for x in d:
    if x["failure_cause"]:
        safe_q = x["question"].encode("ascii", "ignore").decode("ascii")
        print(f"{x['idx']}: {x['category']} ({x['failure_cause']}) -> '{safe_q}' (conf: {x['confidence']})")
