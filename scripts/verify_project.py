#!/usr/bin/env python3
"""Project verification script for Campus Helpdesk AI.

Runs a sequence of checks and produces a structured JSON report:
1. pytest (unit + integration tests)
2. Ruff lint
3. Import smoke tests
4. Coverage report

Exit code 0 only if ALL checks pass.

Usage::

    python scripts/verify_project.py
    python scripts/verify_project.py --phase analytics   # restrict scope
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "data" / "analytics" / "reports"


def _run(cmd: list[str], cwd: Path = PROJECT_ROOT) -> dict:
    """Run a command and return result dict."""
    start = time.perf_counter()
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    elapsed = round(time.perf_counter() - start, 2)
    return {
        "command": " ".join(cmd),
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:] if result.stdout else "",
        "stderr": result.stderr[-2000:] if result.stderr else "",
        "elapsed_sec": elapsed,
        "passed": result.returncode == 0,
    }


def run_pytest(scope: str | None = None) -> dict:
    """Run pytest with coverage."""
    cmd = [
        sys.executable, "-m", "pytest",
        "-v", "--tb=short", "-ra",
    ]
    if scope == "analytics":
        cmd.extend([
            "tests/unit/test_analytics_modules.py",
            "tests/integration/test_analytics_integration.py",
            f"--cov=campus_helpdesk.analytics",
            "--cov-report=term-missing",
        ])
    else:
        cmd.extend([
            "tests/",
            "--cov=campus_helpdesk",
            "--cov-report=term-missing",
        ])
    return _run(cmd)


def run_ruff(scope: str | None = None) -> dict:
    """Run ruff linter."""
    target = "src/campus_helpdesk/analytics/" if scope == "analytics" else "src/"
    cmd = [sys.executable, "-m", "ruff", "check", target]
    return _run(cmd)


def run_smoke_test() -> dict:
    """Import smoke test for the analytics package."""
    cmd = [
        sys.executable, "-c",
        "from campus_helpdesk.analytics import AnalyticsManager, MetricsStore, "
        "EventBus, PipelineTrace, QueryAnalytics, RetrievalAnalytics, "
        "ConversationAnalytics, KnowledgeAnalytics, PerformanceMonitor, "
        "DashboardGenerator, AlertEngine, ReportGenerator; "
        "print('All analytics imports OK')",
    ]
    return _run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Helpdesk project verifier")
    parser.add_argument(
        "--phase",
        choices=["analytics", "all"],
        default="all",
        help="Restrict verification scope",
    )
    args = parser.parse_args()
    scope = args.phase if args.phase != "all" else None

    print("=" * 60)
    print("  Campus Helpdesk — Project Verification")
    print("=" * 60)

    results: dict[str, dict] = {}
    all_passed = True

    # 1. Smoke test
    print("\n[1/3] Import smoke test...")
    results["smoke_test"] = run_smoke_test()
    status = "PASS" if results["smoke_test"]["passed"] else "FAIL"
    print(f"  → {status} ({results['smoke_test']['elapsed_sec']}s)")
    if not results["smoke_test"]["passed"]:
        all_passed = False
        print(f"  STDERR: {results['smoke_test']['stderr'][:500]}")

    # 2. Ruff
    print("\n[2/3] Ruff lint...")
    results["ruff"] = run_ruff(scope)
    status = "PASS" if results["ruff"]["passed"] else "FAIL"
    print(f"  → {status} ({results['ruff']['elapsed_sec']}s)")
    if not results["ruff"]["passed"]:
        all_passed = False
        print(f"  STDOUT: {results['ruff']['stdout'][:500]}")

    # 3. Pytest
    print("\n[3/3] Pytest...")
    results["pytest"] = run_pytest(scope)
    status = "PASS" if results["pytest"]["passed"] else "FAIL"
    print(f"  → {status} ({results['pytest']['elapsed_sec']}s)")
    if not results["pytest"]["passed"]:
        all_passed = False
        # Print last 1000 chars of pytest output
        print(f"  STDOUT (tail):\n{results['pytest']['stdout'][-1000:]}")

    # Summary
    print("\n" + "=" * 60)
    overall = "ALL CHECKS PASSED ✔" if all_passed else "SOME CHECKS FAILED ✘"
    print(f"  Result: {overall}")
    print("=" * 60)

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": scope or "all",
        "all_passed": all_passed,
        "checks": results,
    }
    report_path = REPORT_DIR / f"verification_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
