"""
USB / Offline Transfer Packaging Script
=======================================

Creates a self-contained bundle of the Campus Helpdesk repository suitable for:
1. Copying to a Raspberry Pi OS environment
2. Handing over to another developer via USB drive

Filters out heavy/non-essential build artifacts, Python virtual environments,
logs, temporary test files, and raw scrape caches while retaining all necessary
code, FAISS vector stores, Piper voice models, canonical markdown documentation,
deployment scripts, and configuration templates.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

# Essential directories to copy relative to project root
INCLUDE_DIRS = [
    "src",
    "deployment",
    "data/faiss",
    "data/piper",
    "data/canonical_markdown",
    "scripts",
    "tests",
]

# Essential root-level files
INCLUDE_FILES = [
    "config.yaml",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "CLAUDE.md",
    "RASPBERRY_PI_DEPLOYMENT_GUIDE.md",
    "USB_HANDOVER.md",
    "cleanup_report.md",
    "helpdesk_gui.py",
]

# Directory / file name patterns to exclude
EXCLUDE_PATTERNS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "logs",
    "scratch",
    ".architecture_scan",
    "bvbcet_rag_pipeline",  # Legacy redundant stack
}


def should_exclude(path: Path) -> bool:
    """Check if file/folder matches exclude patterns."""
    for part in path.parts:
        if part in EXCLUDE_PATTERNS or part.endswith(".pyc") or part.endswith(".pyo"):
            return True
    return False


def get_dir_size_bytes(path: Path) -> int:
    """Calculate total size of directory in bytes."""
    total = 0
    if path.is_file():
        return path.stat().st_size
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            if not fp.is_symlink():
                total += fp.stat().st_size
    return total


def bundle_repository(target_dir: Path, zip_output: bool = False) -> None:
    root_dir = Path(__file__).resolve().parent.parent

    print(f"=======================================================================")
    print(f"  BUILDING CAMPUS HELPDESK USB DEPLOYMENT BUNDLE")
    print(f"=======================================================================")
    print(f"Source Root: {root_dir}")
    print(f"Target Path: {target_dir}")

    if target_dir.exists():
        print(f"Target directory exists. Cleaning target directory: {target_dir}")
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy required directories
    for dir_name in INCLUDE_DIRS:
        src_path = root_dir / dir_name
        dest_path = target_dir / dir_name

        if not src_path.exists():
            print(f"[SKIP] Source directory not found: {dir_name}")
            continue

        print(f"[COPYING] Directory: {dir_name} -> {dest_path}")
        shutil.copytree(
            src_path,
            dest_path,
            ignore=lambda folder, contents: [
                c for c in contents if should_exclude(Path(folder) / c)
            ],
            dirs_exist_ok=True,
        )

    # 2. Copy required root files
    for file_name in INCLUDE_FILES:
        src_path = root_dir / file_name
        dest_path = target_dir / file_name

        if not src_path.exists():
            print(f"[SKIP] Source file not found: {file_name}")
            continue

        print(f"[COPYING] File: {file_name}")
        shutil.copyfile(src_path, dest_path)

    # 3. Handle USB_HANDOVER.md if present
    handover_file = root_dir / "USB_HANDOVER.md"
    if handover_file.exists():
        shutil.copyfile(handover_file, target_dir / "USB_HANDOVER.md")

    # Copy .env if present (or fallback to .env.example)
    env_file = root_dir / ".env"
    if env_file.exists():
        print("[COPYING] Environment file (.env)")
        shutil.copyfile(env_file, target_dir / ".env")
    else:
        print("[NOTICE] Creating default .env from .env.example")
        shutil.copyfile(root_dir / ".env.example", target_dir / ".env")

    # Compute final package size
    total_bytes = get_dir_size_bytes(target_dir)
    total_mb = total_bytes / (1024 * 1024)

    print(f"\n[SUMMARY] Bundle assembled successfully at: {target_dir}")
    print(f"[SUMMARY] Total bundle size: {total_mb:.2f} MB")

    if zip_output:
        archive_name = target_dir.with_suffix("")
        print(f"\n[ZIPPING] Compressing bundle to {archive_name}.zip ...")
        archive_path = shutil.make_archive(str(archive_name), "zip", target_dir)
        archive_mb = Path(archive_path).stat().st_size / (1024 * 1024)
        print(f"[SUMMARY] Archive created: {archive_path} ({archive_mb:.2f} MB)")

    print("\n[NEXT STEPS] Transfer folder/zip to USB drive or Raspberry Pi.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bundle Campus Helpdesk repository for USB transfer or Raspberry Pi."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="../campus_helpdesk_usb_bundle",
        help="Target output directory for bundle",
    )
    parser.add_argument(
        "--zip",
        "-z",
        action="store_true",
        help="Create a compressed .zip file of the bundle",
    )
    args = parser.parse_args()

    target_path = Path(args.output).resolve()
    bundle_repository(target_path, zip_output=args.zip)


if __name__ == "__main__":
    main()
