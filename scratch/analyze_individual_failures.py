import json

with open("evaluation/results/e2e_qa_log.json", encoding="utf-8") as f:
    results = json.load(f)

print(f"Total entries: {len(results)}")
print(f"Analyzing only the 'Confidence calibration' failures:")

failed_queries = []
for r in results:
    if r["failure_cause"] == "Confidence calibration":
        failed_queries.append(r)

print(f"Total calibration failures: {len(failed_queries)}")
for i, f_q in enumerate(failed_queries[:20]):
    print(f"\n--- Failure #{i+1} ---")
    print(f"Query: {f_q['question']}")
    print(f"Category: {f_q['category']}")
    print(f"Confidence: {f_q['confidence']}")
    print(f"Sources: {f_q['sources']}")
    print(f"Answer: {f_q['answer']}")
