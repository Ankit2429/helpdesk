import os
import re
import hashlib
from pathlib import Path
import json

canonical_dir = Path("data/canonical_markdown")
all_files = list(canonical_dir.rglob("*.md"))

print(f"Total files found: {len(all_files)}")

# 1. Detect duplicate documents
hashes = {}
duplicates = []
for file_path in all_files:
    content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if h in hashes:
        duplicates.append((file_path, hashes[h]))
    else:
        hashes[h] = file_path

print(f"Duplicate documents: {len(duplicates)}")

# 2. Inconsistent filenames (with hex suffixes like _23ac13)
hex_suffix_pat = re.compile(r"_[a-f0-9]{6}\.md$")
inconsistent_names = []
for file_path in all_files:
    if hex_suffix_pat.search(file_path.name):
        inconsistent_names.append(file_path)

print(f"Inconsistent filenames: {len(inconsistent_names)}")

# 3. Obsolete notices
obsolete_files = []
# Match years like 2013 to 2023
year_pat = re.compile(r"\b(2013|2014|2015|2016|2017|2018|2019|2020|2021|2022|2023)\b")
for file_path in all_files:
    # If the path contains "notices", "events", "calendar", "announcements", "timetable" and old years
    rel_path = file_path.relative_to(canonical_dir).as_posix().lower()
    if any(k in rel_path for k in ["notice", "event", "calendar", "announcement", "timetable", "audit_report", "annual_report"]):
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        found_years = year_pat.findall(content)
        if found_years:
            obsolete_files.append((file_path, list(set(found_years))))

print(f"Obsolete/Historical files: {len(obsolete_files)}")

# 4. Missing metadata
missing_metadata_files = []
for file_path in all_files:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if not content.startswith("---"):
        missing_metadata_files.append(file_path)

print(f"Files missing frontmatter metadata: {len(missing_metadata_files)}")

# Write detailed results to JSON
audit_results = {
    "total_files": len(all_files),
    "duplicates": [str(d[0].relative_to(canonical_dir)) for d in duplicates],
    "inconsistent_filenames": [str(f.relative_to(canonical_dir)) for f in inconsistent_names],
    "obsolete": [{"file": str(o[0].relative_to(canonical_dir)), "years": o[1]} for o in obsolete_files],
    "missing_metadata": [str(m.relative_to(canonical_dir)) for m in missing_metadata_files],
}

with open("scratch/audit_results.json", "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2)

print("Audit complete. Results saved in scratch/audit_results.json")
