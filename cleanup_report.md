# Repository Cleanup & Maintenance Report

## Summary

- **Total Files Removed**: 45
- **Total Storage Recovered**: **12.19 MB**

## Production Assets Preserved (Untouched)

- `src/campus_helpdesk/` (Complete active production codebase)
- `data/faiss/` (FAISS vector store indices & manifests)
- `data/piper/` (ONNX Piper neural TTS models)
- `data/canonical_markdown/` (Canonical campus knowledge base documents)
- `deployment/` (Raspberry Pi systemd unit files & setup scripts)
- `scripts/` (Maintenance, benchmarking & audit utilities)
- `tests/` (Unit and integration test suites)
- `helpdesk_gui.py` (Desktop Kiosk Developer GUI)
- `config.yaml`, `pyproject.toml`, `requirements.txt`, `.env`
- `README.md`, `CLAUDE.md`, `RASPBERRY_PI_DEPLOYMENT_GUIDE.md`, `USB_HANDOVER.md`

## Audit Log of Removed Files

| File Name | Size (KB) | Reason for Removal |
|---|---|---|
| `rag_diagnosis_final.txt` | 52.88 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `rag_diagnosis_output.txt` | 52.51 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `rag_diagnosis_output_v2.txt` | 52.44 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `repo_tree.txt` | 4903.67 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `tree.txt` | 5227.86 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `archive_tree.txt` | 653.24 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `src_tree.txt` | 19.77 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `tests_tree.txt` | 8.53 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `deployment_tree.txt` | 0.46 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `docs_tree.txt` | 1.2 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `scripts_tree.txt` | 0.65 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `chunk_report.json` | 0.19 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `embedding_report.json` | 0.18 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `fast_merge_audit_report.json` | 84.94 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `final_polish_report.json` | 67.91 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `intent_router_verification_report.json` | 3.34 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `metadata_report.json` | 287.4 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `normalize_report.json` | 102.85 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `phase3_verification_report.json` | 3.53 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `post_migration_audit_summary.json` | 4.75 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `rag_verification_results.json` | 6.92 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `real_world_validation_report.json` | 2.31 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `validation_log.json` | 12.55 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `validation_report.txt` | 2.95 KB | Intermediate diagnostic log dump or legacy directory tree listing. |
| `voice_metrics.json` | 0.24 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `audit_results.json` | 3.4 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `benchmark_eval_15_results.json` | 11.89 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `benchmark_eval_344_results.json` | 481.04 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `deduplication_report.json` | 208.86 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `cleaning_report.json` | 69.8 KB | Intermediate batch evaluation dump or temporary test result cache. |
| `analyze_data.py` | 3.37 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `analyze_data_v2.py` | 2.15 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `audit_production.py` | 56.62 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `chat.py` | 8.1 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `config.py` | 1.02 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `diag_e2e.py` | 2.65 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `diag_ollama.py` | 4.15 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `diag_rag.py` | 4.95 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `presence_service.py` | 6.0 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `profile_camera.py` | 5.2 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `stt_service.py` | 8.77 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `tts_service.py` | 9.91 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `ttt_service.py` | 12.71 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `validate_production.py` | 23.75 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |
| `assistant_loop.py` | 8.91 KB | Obsolete root-level duplicate prototype script (active implementation lives in src/campus_helpdesk/). |