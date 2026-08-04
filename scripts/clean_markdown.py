#!/usr/bin/env python3
"""
clean_markdown.py
=================
Cleans scraped markdown documents by removing website boilerplate (menus, footers, 
breadcrumbs, social links, empty sections, duplicate lines) while preserving all
factual contents, sentences, and tables.
"""

import os
import sys
import shutil
import json

def clean_file_content(content):
    lines = content.splitlines(keepends=True)
    total_lines_removed = 0

    # 1. Remove repeated navigation menu & footer block
    # Search for sequence: Connect -> Programs -> Admissions -> Menu
    pattern_sequence = ["connect", "programs", "admissions", "menu"]
    seq_idx = 0
    truncate_at = -1
    
    for idx, line in enumerate(lines):
        cleaned = line.strip().lower().replace("-", "").strip()
        if not cleaned:
            continue
        if cleaned == pattern_sequence[seq_idx]:
            if seq_idx == 0:
                potential_start = idx
            seq_idx += 1
            if seq_idx == len(pattern_sequence):
                truncate_at = potential_start
                break
        else:
            seq_idx = 0
            if cleaned == pattern_sequence[0]:
                potential_start = idx
                seq_idx = 1
                
    if truncate_at != -1:
        while truncate_at > 0 and not lines[truncate_at - 1].strip():
            truncate_at -= 1
        removed = len(lines) - truncate_at
        lines = lines[:truncate_at]
        total_lines_removed += removed

    # 2. Remove breadcrumbs near the top
    start_idx = -1
    for idx in range(min(25, len(lines))):
        line = lines[idx].strip()
        if line.startswith("-") and "home" in line.lower():
            start_idx = idx
            break
            
    if start_idx != -1:
        end_idx = start_idx
        for idx in range(start_idx + 1, min(30, len(lines))):
            line = lines[idx].strip()
            if not line:
                continue
            if line.startswith("-") or line.startswith("*"):
                end_idx = idx
            else:
                break
        removed = end_idx - start_idx + 1
        lines = lines[:start_idx] + lines[end_idx + 1:]
        total_lines_removed += removed

    # 3. Remove Back to Top, Copyright, Social media links
    cleaned_lines = []
    social_patterns = [
        "facebook.com", "twitter.com", "linkedin.com", "youtube.com", 
        "instagram.com", "[facebook]", "[twitter]", "[linkedin]", 
        "[youtube]", "[instagram]"
    ]
    
    for line in lines:
        line_lower = line.lower()
        if "back to top" in line_lower:
            total_lines_removed += 1
            continue
        if "copyright" in line_lower or "copyright ©" in line_lower:
            total_lines_removed += 1
            continue
        if any(pat in line_lower for pat in social_patterns):
            total_lines_removed += 1
            continue
        cleaned_lines.append(line)
    lines = cleaned_lines

    # 4. Remove empty Markdown sections
    cleaned_lines = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.strip().startswith("#"):
            next_idx = idx + 1
            is_empty = True
            while next_idx < len(lines):
                next_line = lines[next_idx].strip()
                if next_line:
                    if next_line.startswith("#"):
                        is_empty = True
                    else:
                        is_empty = False
                    break
                next_idx += 1
            
            if is_empty:
                total_lines_removed += 1
                idx = next_idx
                continue
        cleaned_lines.append(line)
        idx += 1
    lines = cleaned_lines

    # 5. Remove repeated blank lines & separators
    cleaned_lines = []
    prev_empty = False
    prev_hr = False
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            if prev_empty:
                total_lines_removed += 1
                continue
            prev_empty = True
        else:
            prev_empty = False
            
        is_hr = line_strip in ("---", "***", "___", "- - -", "* * *")
        if is_hr:
            if prev_hr:
                total_lines_removed += 1
                continue
            prev_hr = True
        else:
            prev_hr = False
            
        cleaned_lines.append(line)
    lines = cleaned_lines

    # 6. Heading spacing (Exactly one blank line before and after headings)
    final_lines = []
    for idx, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith("#"):
            if final_lines and final_lines[-1].strip():
                final_lines.append("\n")
            final_lines.append(line)
        else:
            if final_lines and final_lines[-1].strip().startswith("#") and line_strip:
                final_lines.append("\n")
            final_lines.append(line)
            
    # Combine back to text
    cleaned_content = "".join(final_lines)
    return cleaned_content, total_lines_removed

def main():
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    markdown_root = os.path.normpath(os.path.join(workspace_root, "data", "canonical_markdown"))
    backup_root = os.path.normpath(os.path.join(workspace_root, "data", "canonical_markdown_backup"))
    
    if not os.path.exists(markdown_root):
        print(f"Error: Markdown root path '{markdown_root}' does not exist.")
        sys.exit(1)
        
    # Create backup before modifying
    print(f"Creating backup of {markdown_root} to {backup_root}...")
    if os.path.exists(backup_root):
        shutil.rmtree(backup_root)
    shutil.copytree(markdown_root, backup_root)
    print("Backup completed successfully.")
    
    files_processed = 0
    total_lines_removed = 0
    files_skipped = 0
    empty_documents_found = 0
    error_count = 0
    
    processed_list = []
    
    for root, dirs, files in os.walk(markdown_root):
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                rel_path = os.path.relpath(fp, markdown_root)
                
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as file_handle:
                        content = file_handle.read()
                        
                    cleaned_content, lines_removed = clean_file_content(content)
                    
                    # Check if document is empty after cleaning
                    # (only contains source urls or metadata line count < 4)
                    stripped_clean = cleaned_content.strip()
                    lines_clean = stripped_clean.splitlines()
                    is_empty = False
                    if not stripped_clean:
                        is_empty = True
                    else:
                        # Check if it only contains H1 headers and Source URL lines
                        real_content = False
                        for line in lines_clean:
                            line_s = line.strip()
                            if line_s and not line_s.startswith("#") and not line_s.startswith("**Source URL:**") and not line_s.startswith("**PDF Source:**"):
                                real_content = True
                                break
                        if not real_content:
                            is_empty = True
                            
                    if is_empty:
                        empty_documents_found += 1
                        print(f"[EMPTY] {rel_path} contains no body content after cleaning.")
                        
                    # Write cleaned content
                    with open(fp, "w", encoding="utf-8") as file_handle:
                        file_handle.write(cleaned_content)
                        
                    files_processed += 1
                    total_lines_removed += lines_removed
                    processed_list.append({
                        "file": rel_path.replace(os.sep, "/"),
                        "lines_removed": lines_removed,
                        "status": "CLEANED" if not is_empty else "EMPTY"
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to process {rel_path}: {e}")
                    error_count += 1
                    files_skipped += 1
                    
    # Write cleaning_report.json
    report_json_path = os.path.join(workspace_root, "cleaning_report.json")
    try:
        with open(report_json_path, "w", encoding="utf-8") as rf:
            json.dump({
                "files_processed_count": files_processed,
                "total_lines_removed": total_lines_removed,
                "files_skipped_count": files_skipped,
                "empty_documents_count": empty_documents_found,
                "errors_count": error_count,
                "details": processed_list
            }, rf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write report JSON: {e}")
        error_count += 1

    print("\n=========================================")
    print("      MARKDOWN CLEANING JOB SUMMARY")
    print("=========================================")
    print(f"Files Processed        : {files_processed}")
    print(f"Total Lines Removed    : {total_lines_removed}")
    print(f"Files Skipped          : {files_skipped}")
    print(f"Empty Documents Found  : {empty_documents_found}")
    print(f"Errors Encountered     : {error_count}")
    print(f"JSON Report Generated  : {report_json_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
