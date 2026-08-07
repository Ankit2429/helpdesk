import os
import hashlib
from collections import defaultdict
from pathlib import Path

def get_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def find_duplicates():
    src_dir = Path("src/campus_helpdesk")
    
    # 1. Duplicate filenames (potential duplicate modules)
    filename_map = defaultdict(list)
    hash_map = defaultdict(list)
    
    for root, _, files in os.walk(src_dir):
        if "__pycache__" in root: continue
        for file in files:
            if file.endswith('.py'):
                path = Path(root) / file
                filename_map[file].append(str(path))
                hash_map[get_hash(path)].append(str(path))
                
    print("--- DUPLICATE FILENAMES ---")
    for fname, paths in filename_map.items():
        if len(paths) > 1 and fname != "__init__.py":
            print(f"{fname}: {paths}")
            
    print("\n--- IDENTICAL FILES ---")
    for h, paths in hash_map.items():
        if len(paths) > 1 and not all(p.endswith('__init__.py') for p in paths):
            print(f"Identical content: {paths}")

if __name__ == "__main__":
    find_duplicates()
