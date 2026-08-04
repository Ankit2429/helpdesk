import json

with open("evaluation/results/audit_failures_details.json", encoding="utf-8") as f:
    records = json.load(f)

md_output = ""

for rec in records:
    idx = rec["idx"]
    query = rec["query"]
    cat = rec["category"]
    rewritten = rec["rewritten"]
    score = rec["score"]
    top_reranker = rec["top_reranker"]
    top_distance = rec["top_distance"]
    chunks = rec["chunks"]
    
    # Analyze why it was rejected
    # Thresholds: score >= 0.35, top_reranker >= 0.1, top_distance <= 1.2
    reasons = []
    if score < 0.35:
        reasons.append(f"Composite score ({score}) fell below 0.35")
    if top_reranker < 0.1:
        reasons.append(f"Top reranker score ({top_reranker}) fell below 0.1")
    if top_distance > 1.2:
        reasons.append(f"Top distance ({top_distance}) was above 1.2")
        
    reason_str = ", ".join(reasons)
    
    # Determine if correct or overly conservative
    # Conversational or out-of-domain should be rejected (Correct).
    # Valid campus queries should be accepted (Overly conservative).
    if cat in ["Greetings", "Small talk", "Out-of-domain questions", "Programming questions", "Impossible questions", "Ambiguous questions"]:
        assessment = "CORRECT REJECTION (Out-of-domain / Ambiguous / Conversational / Impossible)"
    else:
        assessment = "OVERLY CONSERVATIVE (Valid Campus/Student Query)"
        
    md_output += f"""### Query #{idx}: "{query}"
- **Category**: {cat}
- **Rewritten**: `{rewritten}`
- **Composite Score**: `{score}` (Threshold: 0.35)
- **Top Reranker Score**: `{top_reranker}` (Threshold: 0.1)
- **Top Distance**: `{top_distance}` (Threshold: 1.2)
- **Decision**: REJECT
- **Rejection Reason**: {reason_str}
- **Assessment**: **{assessment}**
- **Retrieved Chunks**:
"""
    for j, c in enumerate(chunks[:2]):
        md_output += f"  - Chunk {j+1}: `[{c['source']}]` (Distance: {c['distance']}) - Snippet: {c['text'][:150]}...\n"
    md_output += "\n---\n"

with open("evaluation/results/failures_analysis.md", "w", encoding="utf-8") as f:
    f.write(md_output)

print("Generated failures_analysis.md")
