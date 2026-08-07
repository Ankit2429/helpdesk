"""
Repository Cleanup Utility
==========================

Audits and cleans obsolete, duplicate, and intermediate diagnostic files from the project root.
Generates `cleanup_report.md` detailing every removed file, file size, and justification.
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Files identified for cleanup (obsolete/duplicate root scripts & diagnostic dumps)
TARGET_FILES = [
    # Intermediate diagnostic dumps & tree logs
    "rag_diagnosis_final.txt",
    "rag_diagnosis_output.txt",
    "rag_diagnosis_output_v2.txt",
    "repo_tree.txt",
    "tree.txt",
    "archive_tree.txt",
    "src_tree.txt",
    "tests_tree.txt",
    "deployment_tree.txt",
    "docs_tree.txt",
    "scripts_tree.txt",
    # Intermediate JSON audit logs
    "chunk_report.json",
    "embedding_report.json",
    "fast_merge_audit_report.json",
    "final_polish_report.json",
    "intent_router_verification_report.json",
    "metadata_report.json",
    "normalize_report.json",
    "phase3_verification_report.json",
    "post_migration_audit_summary.json",
    "rag_verification_results.json",
    "real_world_validation_report.json",
    "validation_log.json",
    "validation_report.txt",
    "voice_metrics.json",
    "audit_results.json",
    "benchmark_eval_15_results.json",
    "benchmark_eval_344_results.json",
    "deduplication_report.json",
    "cleaning_report.json",
    # Obsolete root-level duplicate prototype scripts (active code lives in src/campus_helpdesk/)
    "analyze_data.py",
    "analyze_data_v2.py",
    "audit_production.py",
    "chat.py",
    "config.py",
    "diag_e2e.py",
    "diag_ollama.py",
    "diag_rag.py",
    "presence_service.py",
    "profile_camera.py",
    "stt_service.py",
    "tts_service.py",
    "ttt_service.py",
    "validate_production.py",
    "assistant_loop.py",
]

# File category justifications
JUSTIFICATIONS = {
    ".txt": "Intermediate diagnostic log dump or legacy directory tree listing.",
    ".json": "Intermediate batch evaluation dump or temporary test result cache.",
    ".py": "Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/).",
}


def perform_cleanup():
    print("=======================================================================")
    print("  CAMPUS HELPDESK — REPOSITORY CLEANUP & AUDIT")
    print("=======================================================================")

    removed_records = []
    total_freed_bytes = 0

    for file_name in TARGET_FILES:
        file_path = ROOT_DIR / file_name
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            ext = file_path.suffix.lower()
            reason = JUSTIFICATIONS.get(ext, "Obsolete build artifact or temporary file.")

            try:
                os.remove(file_path)
                total_freed_bytes += size_bytes
                removed_records.append({
                    "name": file_name,
                    "size_kb": round(size_bytes / 1024, 2),
                    "reason": reason,
                })
                print(f"[REMOVED] {file_name:<40} ({size_bytes / 1024:.1f} KB)")
            except Exception as e:
                print(f"[ERROR] Could not remove {file_name}: {e}")
        else:
            print(f"[SKIP] Not found: {file_name}")

    total_freed_mb = total_freed_bytes / (1024 * 1024)

    # Generate cleanup_report.md
    report_path = ROOT_DIR / "cleanup_report.md"
    report_lines = [
        "# Repository Cleanup & Maintenance Report",
        "",
        "## Summary",
        "",
        f"- **Total Files Removed**: {len(removed_records)}",
        f"- **Total Storage Recovered**: **{total_freed_mb:.2f} MB**",
        "",
        "## Production Assets Preserved (Untouched)",
        "",
        "- `src/campus_helpdesk/` (Complete active production codebase)",
        "- `data/faiss/` (FAISS vector store indices & manifests)",
        "- `data/piper/` (ONNX Piper neural TTS models)",
        "- `data/canonical_markdown/` (Canonical campus knowledge base documents)",
        "- `deployment/` (Raspberry Pi systemd unit files & setup scripts)",
        "- `scripts/` (Maintenance, benchmarking & audit utilities)",
        "- `tests/` (Unit and integration test suites)",
        "- `helpdesk_gui.py` (Desktop Kiosk Developer GUI)",
        "- `config.yaml`, `pyproject.toml`, `requirements.txt`, `.env`",
        "- `README.md`, `CLAUDE.md`, `RASPBERRY_PI_DEPLOYMENT_GUIDE.md`, `USB_HANDOVER.md`",
        "",
        "## Audit Log of Removed Files",
        "",
        "| File Name | Size (KB) | Reason for Removal |",
        "|---|---|---|",
    ]

    for rec in removed_records:
        report_lines.append(f"| `{rec['name']}` | {rec['size_kb']} KB | {rec['reason']} |")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    print("\n=======================================================================")
    print(f"  CLEANUP COMPLETE: Removed {len(removed_records)} files | Freed {total_freed_mb:.2f} MB")
    print(f"  Report generated at: {report_path}")
    print("=======================================================================")


if __name__ == "__main__":
    perform_cleanup()
