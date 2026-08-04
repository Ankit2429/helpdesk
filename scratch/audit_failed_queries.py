import json
from campus_helpdesk.touch_app import build_chat_service

with open("evaluation/results/e2e_qa_log.json", encoding="utf-8") as f:
    results = json.load(f)

# Find failed queries
failed_items = [r for r in results if r["failure_cause"] == "Confidence calibration"]

print("Initializing RAG chat service...")
service = build_chat_service()
pipeline = service._rag_pipeline

audit_records = []

for idx, f_q in enumerate(failed_items):
    query = f_q["question"]
    category = f_q["category"]
    
    # Run retrieval
    rewritten_query = service._query_rewriter.rewrite(query)
    search_results = pipeline.search(rewritten_query, limit=5)
    
    # Evaluate confidence
    confidence_assessment = service.confidence_engine.evaluate(search_results)
    
    score = confidence_assessment.confidence_score
    level = confidence_assessment.confidence_level
    top_reranker = confidence_assessment.top_reranker_score
    top_distance = confidence_assessment.top_distance
    
    chunks_info = []
    for match in search_results:
        chunks_info.append({
            "source": match.document.metadata.get("source"),
            "distance": match.distance,
            "text": match.document.content[:200].replace("\n", " ")
        })
        
    audit_records.append({
        "idx": f_q["idx"],
        "query": query,
        "category": category,
        "rewritten": rewritten_query,
        "score": score,
        "level": level,
        "top_reranker": top_reranker,
        "top_distance": top_distance,
        "chunks": chunks_info
    })

# Write the detailed audit findings to a json file
with open("evaluation/results/audit_failures_details.json", "w", encoding="utf-8") as f:
    json.dump(audit_records, f, indent=2)

print(f"Audited {len(audit_records)} failures and wrote to evaluation/results/audit_failures_details.json")
