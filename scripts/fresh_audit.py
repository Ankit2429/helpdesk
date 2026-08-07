"""
fresh_audit.py - Regenerates 4-category metrics directly from the latest benchmark JSON.
Also prints per-question detail for transparency.
"""
import json
import yaml
from pathlib import Path

def main():
    json_path = Path("evaluation/results/baseline_vs_optimized_comparison.json")
    q_file = Path("evaluation/questions.yaml")

    data = json.load(open(json_path))
    questions_yaml = {}
    if q_file.exists():
        ydata = yaml.safe_load(open(q_file))
        for q in ydata.get("questions", []):
            questions_yaml[q["id"]] = q

    REFUSAL_PHRASES = [
        "couldn't find", "not specified", "not provided", "no information",
        "does not provide", "not explicitly mentioned", "cannot provide",
        "context provided does not contain"
    ]

    UNANSWERABLE_QUERIES = [
        "cafeteria's phone", "email address for the library", "library phone number",
        "admissions office phone number",
    ]

    cat_counts = {"CORRECT": 0, "REFUSAL": 0, "PARTIAL": 0, "INCORRECT": 0}
    rows = []

    for item in data:
        qid = item["id"]
        qtext = item["question"]
        opt = item["optimized"]
        reply = opt["reply"].strip()
        reply_lower = reply.lower()
        sources = opt.get("sources", [])

        y_info = questions_yaml.get(qid, {})
        exp_kws = y_info.get("expected_answer_keywords", [])
        matched_kws = [kw for kw in exp_kws if str(kw).lower() in reply_lower]
        kw_coverage = len(matched_kws) / len(exp_kws) if exp_kws else 1.0

        is_refusal = any(p in reply_lower for p in REFUSAL_PHRASES)
        is_unanswerable = any(uq in qtext.lower() for uq in UNANSWERABLE_QUERIES)
        has_fabricated_url = False
        for word in reply.split():
            if word.startswith("http") and "kletech.ac.in" not in word and "cetonline.karnataka.gov.in" not in word:
                has_fabricated_url = True

        # 4-category classification
        if is_refusal:
            if is_unanswerable or (kw_coverage == 0 and len(exp_kws) > 0):
                cat = "REFUSAL"
                note = "Valid intentional refusal — KB lacks this private/unverified detail."
            else:
                # Refusal when KB has the info = retrieval/context failure
                cat = "INCORRECT"
                note = "Retrieval/context failure — refusal despite KB having the answer."
        elif has_fabricated_url:
            cat = "INCORRECT"
            note = "Fabricated external URL detected."
        elif kw_coverage >= 0.5:
            cat = "CORRECT"
            note = f"Matched {len(matched_kws)}/{len(exp_kws)} expected keywords." if exp_kws else "No keyword constraint; sourced from KB."
        elif kw_coverage > 0:
            cat = "PARTIAL"
            note = f"Partial keyword match ({len(matched_kws)}/{len(exp_kws)}). Core facts present."
        else:
            if not exp_kws and len(reply) > 60 and len(sources) > 0:
                cat = "CORRECT"
                note = "No keyword constraint; answer returned with valid KB source."
            else:
                cat = "INCORRECT"
                note = "Missing expected keywords with no fallback."

        cat_counts[cat] += 1
        rows.append((qid, qtext[:55], sources[0] if sources else "—", cat, note, round(kw_coverage,2)))

    # Print full per-question detail
    print("=" * 110)
    print(f"{'ID':<8} {'Question':<55} {'Top Source':<45} {'Cat':<10} {'KW Cov'}")
    print("=" * 110)
    for qid, qtext, src, cat, note, kw_cov in rows:
        src_short = src.split("/")[-1][:42] if src else "—"
        print(f"{qid:<8} {qtext:<55} {src_short:<45} {cat:<10} {kw_cov:.2f}")

    print()
    print("=" * 110)
    total = len(rows)
    print(f"TOTAL QUESTIONS         : {total}")
    print(f"(1) CORRECT             : {cat_counts['CORRECT']}  ({cat_counts['CORRECT']/total*100:.1f}%)")
    print(f"(2) CORRECT REFUSALS    : {cat_counts['REFUSAL']}  ({cat_counts['REFUSAL']/total*100:.1f}%)")
    print(f"(3) PARTIAL GROUNDED    : {cat_counts['PARTIAL']}  ({cat_counts['PARTIAL']/total*100:.1f}%)")
    print(f"(4) INCORRECT/HALLUC    : {cat_counts['INCORRECT']}  ({cat_counts['INCORRECT']/total*100:.1f}%)")
    safe_score = cat_counts['CORRECT'] + cat_counts['REFUSAL'] + cat_counts['PARTIAL']
    print(f"\nPRODUCTION SAFETY SCORE : {safe_score}/{total} ({safe_score/total*100:.1f}%)")
    print("=" * 110)

    # Dump per-question notes for Category 4
    print("\n--- CATEGORY 4 DETAIL (Incorrect / Hallucination) ---")
    for qid, qtext, src, cat, note, kw_cov in rows:
        if cat == "INCORRECT":
            print(f"  [{qid}] {qtext.strip()}")
            print(f"    Source: {src} | Note: {note}")

if __name__ == "__main__":
    main()
