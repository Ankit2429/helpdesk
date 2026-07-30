import os
import json
import yaml
import pathlib
from collections import Counter

# Paths (project root two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
METRICS_JSON = os.path.join(BASE_DIR, "results", "real_world_metrics.json")
FAILURE_CSV = os.path.join(BASE_DIR, "results", "failure_summary.csv")
REPORT_MD = os.path.join(BASE_DIR, "evaluation", "reports", "real_world_validation_report.md")

def load_metrics():
    with open(METRICS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def load_failure_summary():
    summary = []
    with open(FAILURE_CSV, "r", encoding="utf-8") as f:
        next(f)  # skip header
        for line in f:
            if not line.strip():
                continue
            cat, cnt = line.strip().split(",")
            summary.append((cat, int(cnt)))
    summary.sort(key=lambda x: x[1], reverse=True)
    return summary

def generate_report():
    metrics = load_metrics()
    failures = load_failure_summary()

    best_metrics = sorted(metrics.items(), key=lambda x: x[1], reverse=True)[:3]
    worst_metrics = sorted(metrics.items(), key=lambda x: x[1])[:3]

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as md:
        md.write("# Real‑World Validation Report\n\n")
        md.write("## Overall Metrics\n\n")
        for name, value in metrics.items():
            if isinstance(value, float):
                md.write(f"- **{name.replace('_', ' ').title()}**: {value:.4f}\n")
            else:
                md.write(f"- **{name.replace('_', ' ').title()}**: {value}\n")
        md.write("\n---\n\n")
        md.write("## Best Performing Aspects\n\n")
        for k, v in best_metrics:
            md.write(f"- **{k.replace('_', ' ').title()}**: {v:.4f}\n")
        md.write("\n## Worst Performing Aspects\n\n")
        for k, v in worst_metrics:
            md.write(f"- **{k.replace('_', ' ').title()}**: {v:.4f}\n")
        md.write("\n---\n\n")
        md.write("## Most Common Failure Categories\n\n")
        md.write("| Failure Category | Count |\n|---|---|\n")
        for cat, cnt in failures[:10]:
            md.write(f"| {cat} | {cnt} |\n")
        md.write("\n---\n\n")
        md.write("## Recommendations before Voice Integration\n\n")
        md.write("- Improve citation validation to reduce *Wrong citation* failures.\n")
        md.write("- Tighten prompt‑injection filters; ensure the model never obeys disallowed instructions.\n")
        md.write("- Increase confidence calibration (lower ECE) to trust confidence scores for voice fallback.\n")
        md.write("- Expand memory window or add explicit session‑level summarisation to avoid *Memory failure* on repeated queries.\n")
        md.write("- Optimize latency (target < 500 ms average) to meet real‑time voice response requirements.\n")
        md.write(f"\nReport generated at: {pathlib.Path(REPORT_MD).as_uri()}\n")
    print(f"Report written to {REPORT_MD}")

if __name__ == "__main__":
    generate_report()
