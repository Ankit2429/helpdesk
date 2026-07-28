import os
import hashlib
import re
from collections import defaultdict
from pathlib import Path

# Paths
base_path = Path("archive/bvbcet_scraper/knowledge_base/markdown/")

# Metrics
total_files = 0
total_size = 0
empty_files = 0
tiny_files = 0
oversized_files = 0
missing_titles = 0
missing_metadata = 0
broken_markdown = 0
pdf_artifacts = 0
nav_noise = 0

content_hashes = defaultdict(list)
near_dup_hashes = defaultdict(list)

def get_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def get_normalized_hash(text):
    # Remove all whitespace and non-alphanumeric chars for near-dup detection
    normalized = re.sub(r'\W+', '', text.lower())
    return get_hash(normalized)

for root, _, files in os.walk(base_path):
    for file in files:
        if file.endswith(".md"):
            filepath = Path(root) / file
            total_files += 1

            size = filepath.stat().st_size
            total_size += size

            if size == 0:
                empty_files += 1
                continue

            if size < 1024:
                tiny_files += 1

            if size > 1024 * 100:
                oversized_files += 1

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content_hashes[get_hash(content)].append(str(filepath))
            near_dup_hashes[get_normalized_hash(content)].append(str(filepath))

            # Check metadata
            if not content.startswith("---"):
                missing_metadata += 1

            # Check titles
            if not re.search(r'^#\s+\w+', content, re.MULTILINE):
                missing_titles += 1

            # Check PDF artifacts (e.g., repeated "Page x of y" or weird headers)
            if re.search(r'Page \d+ of \d+|Scanned by|CamScanner', content, re.IGNORECASE) or len(re.findall(r'(\n\s*\n){3,}', content)) > 5:
                pdf_artifacts += 1

            # Check Nav Noise (e.g., repeating menus)
            if re.search(r'Home\s+\|\s+About\s+\|\s+Contact', content, re.IGNORECASE) or "Skip to content" in content:
                nav_noise += 1

            # Check broken markdown (unmatched code blocks)
            if content.count("```") % 2 != 0:
                broken_markdown += 1

duplicate_groups = {k: v for k, v in content_hashes.items() if len(v) > 1}
near_dup_groups = {k: v for k, v in near_dup_hashes.items() if len(v) > 1}

num_duplicates = sum(len(v) - 1 for v in duplicate_groups.values())
num_near_duplicates = sum(len(v) - 1 for v in near_dup_groups.values()) - num_duplicates

print(f"Total Files: {total_files}")
print(f"Total Size (bytes): {total_size}")
print(f"Empty Files: {empty_files}")
print(f"Tiny Files (<1KB): {tiny_files}")
print(f"Oversized Files (>100KB): {oversized_files}")
print(f"Missing Metadata: {missing_metadata}")
print(f"Missing Titles: {missing_titles}")
print(f"PDF Artifacts: {pdf_artifacts}")
print(f"Nav Noise: {nav_noise}")
print(f"Broken Markdown: {broken_markdown}")
print(f"Duplicate Files: {num_duplicates}")
print(f"Near Duplicate Files: {num_near_duplicates}")
print(f"Unique Canonical Documents: {len(near_dup_hashes)}")

# Print a few duplicates for report
print("\nSample Exact Duplicates:")
for i, (k, v) in enumerate(duplicate_groups.items()):
    if i < 3:
        print(f"Group {i+1}: {len(v)} files (e.g. {v[0]})")
