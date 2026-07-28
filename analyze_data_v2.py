import os
import hashlib
import re
from collections import defaultdict
from pathlib import Path

base_path = Path("archive/bvbcet_scraper/knowledge_base/markdown/")

total_files = 0
total_size = 0
tiny_files = []
oversized_files = []

content_hashes = defaultdict(list)

# A more aggressive near-duplicate checker looking at semantic text chunks
def get_signature(text):
    # Strip URLs, generic titles, headers, standard boilerplates
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'#.*', '', text)
    text = re.sub(r'\*\*(Source URL|Source).*?\*\*', '', text)
    # Return hash of alphanumeric only
    return hashlib.md5(re.sub(r'\W+', '', text.lower()).encode()).hexdigest()

for root, _, files in os.walk(base_path):
    for file in files:
        if file.endswith(".md"):
            filepath = Path(root) / file
            total_files += 1

            size = filepath.stat().st_size
            total_size += size

            if size < 1024:
                tiny_files.append(str(filepath))
            if size > 1024 * 100:
                oversized_files.append(str(filepath))

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content_hashes[get_signature(content)].append(str(filepath))

dup_groups = {k: v for k, v in content_hashes.items() if len(v) > 1}
num_dups = sum(len(v) - 1 for v in dup_groups.values())
size_savings = 0

for v in dup_groups.values():
    # Sum sizes of all but the first file
    for f in v[1:]:
        size_savings += Path(f).stat().st_size

print(f"Total Files: {total_files}")
print(f"Total Size: {total_size / 1024 / 1024:.2f} MB")
print(f"Semantic Duplicates: {num_dups}")
print(f"Unique Canonical Documents: {len(content_hashes)}")
print(f"Size Savings from Deduplication: {size_savings / 1024 / 1024:.2f} MB")
print(f"Tiny Files count: {len(tiny_files)}")
print(f"Oversized Files count: {len(oversized_files)}")

# Find specific groups
programs_dups = 0
for v in dup_groups.values():
    if any("programs_" in f for f in v):
        programs_dups += len(v)

print(f"Programs Duplicates count: {programs_dups}")
