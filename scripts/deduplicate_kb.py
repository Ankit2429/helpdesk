#!/usr/bin/env python3
"""
deduplicate_kb.py
=================
Parses duplicate groupings, keeps the canonical document, and moves ONLY
the listed duplicate files to archive/duplicates/ preserving original directory structure.
"""

import os
import sys
import shutil
import json
import re

def main():
    # Paths configuration
    workspace_root = r"d:\helpdesk\anti"
    kb_root = os.path.normpath(os.path.join(workspace_root, "archive", "bvbcet_scraper", "knowledge_base"))
    archive_dup_root = os.path.normpath(os.path.join(workspace_root, "archive", "duplicates"))
    
    # Try to load the complete duplicate metadata from scratch path first
    metadata_path = r"C:\Users\godby\.gemini\antigravity-ide\brain\af23156f-02c1-4f0b-9446-7c0b642a6473\scratch\dup_metadata.json"
    report_path = r"C:\Users\godby\.gemini\antigravity-ide\brain\af23156f-02c1-4f0b-9446-7c0b642a6473\duplicate_report.md"
    
    groups = []
    
    if os.path.exists(metadata_path):
        print(f"Loading duplicate groupings from metadata json: {metadata_path}")
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    groups.append({
                        "canonical": os.path.normpath(item["canonical"]["rel_path"]),
                        "reason": item.get("reason", "Semantic duplicate match"),
                        "duplicates": [os.path.normpath(d["rel_path"]) for d in item["duplicates"]]
                    })
        except Exception as e:
            print(f"Error loading {metadata_path}: {e}")
            
    if not groups and os.path.exists(report_path):
        print(f"Loading duplicate groupings from markdown report: {report_path}")
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            current_canonical = None
            current_duplicates = []
            current_reason = ""
            
            canon_pattern = re.compile(r"^\*\s+\*\*Canonical Document\*\*:\s+`knowledge_base/(.*?)`")
            reason_pattern = re.compile(r"^\*\s+\*\*Reason for Duplication\*\*:\s+(.*)")
            table_row_pattern = re.compile(r"^\|\s+`knowledge_base/(.*?)`\s+\|")
            
            for line in lines:
                line = line.strip()
                canon_match = canon_pattern.match(line)
                if canon_match:
                    if current_canonical:
                        groups.append({
                            "canonical": current_canonical,
                            "reason": current_reason,
                            "duplicates": current_duplicates
                        })
                    current_canonical = os.path.normpath(canon_match.group(1))
                    current_duplicates = []
                    current_reason = ""
                    continue
                    
                reason_match = reason_pattern.match(line)
                if reason_match:
                    current_reason = reason_match.group(1)
                    continue
                    
                table_match = table_row_pattern.match(line)
                if table_match:
                    dup_file = os.path.normpath(table_match.group(1))
                    if "..." not in dup_file:
                        current_duplicates.append(dup_file)
                        
            if current_canonical:
                groups.append({
                    "canonical": current_canonical,
                    "reason": current_reason,
                    "duplicates": current_duplicates
                })
        except Exception as e:
            print(f"Error parsing markdown: {e}")
            
    if not groups:
        print("Error: No duplicate groupings found to process.")
        sys.exit(1)
        
    print(f"Loaded {len(groups)} duplicate groups to process.")
    
    # Track statistics
    groups_processed = 0
    files_moved = 0
    files_skipped = 0
    canonical_kept = 0
    error_count = 0
    
    report_data = []
    
    for g in groups:
        canon_rel = g["canonical"]
        canon_path = os.path.join(kb_root, canon_rel)
        
        # Safety Check: Verify Canonical Document Exists
        if not os.path.exists(canon_path):
            print(f"[ERROR] Canonical document missing: {canon_rel}. Skipping group.")
            error_count += 1
            files_skipped += len(g["duplicates"])
            continue
            
        groups_processed += 1
        canonical_kept += 1
        moved_list = []
        
        # Move duplicates
        for dup_rel in g["duplicates"]:
            # Safety Check: Never move the canonical document
            if dup_rel == canon_rel:
                print(f"[SKIP] Skipping canonical self-match: {dup_rel}")
                files_skipped += 1
                continue
                
            src_path = os.path.join(kb_root, dup_rel)
            
            # Safety Check: Skip missing files
            if not os.path.exists(src_path):
                print(f"[SKIP] Duplicate file missing: {dup_rel}")
                files_skipped += 1
                continue
                
            dest_path = os.path.join(archive_dup_root, dup_rel)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Perform movement
            try:
                # Log every move
                print(f"[MOVE] Moving duplicate from {dup_rel} to archive...")
                shutil.move(src_path, dest_path)
                moved_list.append(dup_rel)
                files_moved += 1
            except Exception as e:
                print(f"[ERROR] Failed to move {dup_rel}: {e}")
                error_count += 1
                
        report_data.append({
            "canonical_file": canon_rel.replace(os.sep, "/"),
            "moved_files": [m.replace(os.sep, "/") for m in moved_list],
            "reason": g["reason"],
            "duplicate_count": len(moved_list)
        })
        
    # Write deduplication_report.json
    json_report_path = os.path.join(workspace_root, "deduplication_report.json")
    try:
        with open(json_report_path, "w", encoding="utf-8") as jf:
            json.dump(report_data, jf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write json report: {e}")
        error_count += 1
        
    print("\n=========================================")
    print("      DEDUPLICATION JOB SUMMARY")
    print("=========================================")
    print(f"Duplicate Groups Processed : {groups_processed}")
    print(f"Files Moved to Archive     : {files_moved}")
    print(f"Files Skipped              : {files_skipped}")
    print(f"Canonical Files Kept       : {canonical_kept}")
    print(f"Errors Encountered         : {error_count}")
    print(f"JSON Report Generated      : {json_report_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
