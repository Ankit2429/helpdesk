#!/usr/bin/env python3
"""
final_polish.py
===============
Performs the final polish pass on markdown documents in the knowledge base.
Extracts cleaner human-like titles from content, stores page metadata,
and removes PDF repetitive artifacts while preserving factual content and structure.
"""

import os
import sys
import json
import re

def parse_yaml(yaml_text):
    meta = {}
    for line in yaml_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            elif v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            if v.startswith("[") and v.endswith("]"):
                try:
                    v = json.loads(v.replace("'", '"'))
                except:
                    pass
            meta[k] = v
    return meta

def serialize_yaml(meta):
    lines = ["---"]
    order = [
        "title", "category", "subcategory", "document_type", "department", 
        "campus", "source_url", "scrape_date", "language", "keywords", 
        "aliases", "last_modified", "page_start", "page_end"
    ]
    for key in order:
        if key in meta:
            val = meta[key]
            if isinstance(val, list):
                # Ensure no single quotes in JSON output
                lines.append(f"{key}: {json.dumps(val)}")
            elif val is None or val == "":
                lines.append(f"{key}: \"\"")
            else:
                val_str = str(val).replace('"', '\\"')
                lines.append(f"{key}: \"{val_str}\"")
                
    for key, val in meta.items():
        if key not in order:
            if isinstance(val, list):
                lines.append(f"{key}: {json.dumps(val)}")
            elif val is None or val == "":
                lines.append(f"{key}: \"\"")
            else:
                val_str = str(val).replace('"', '\\"')
                lines.append(f"{key}: \"{val_str}\"")
    lines.append("---")
    return "\n".join(lines)

def improve_title(filename, content, current_title):
    # If the title is not a PDF Document placeholder, we can keep it
    if not current_title.startswith("PDF Document:"):
        return current_title
        
    base = os.path.splitext(filename)[0]
    base_clean = re.sub(r"^\d+[a-z\d]+[_-]", "", base)
    base_clean = re.sub(r"^\d+[a-z\d]+", "", base_clean)
    
    first_20_lines = content.splitlines()[:30]
    content_title = ""
    
    # Heuristic 1: Look for Program/Department details
    program = ""
    batch = ""
    for line in first_20_lines:
        line_s = line.strip()
        if line_s.startswith("Program:"):
            program = line_s.replace("Program:", "").strip()
        elif "(" in line_s and "batch)" in line_s.lower():
            batch = line_s.strip()
            
    if program:
        content_title = program
        if batch:
            content_title += f" Curriculum {batch}"
        else:
            content_title += " Curriculum"
            
    if not content_title:
        # Heuristic 2: Find H1 header inside body
        lines_non_empty = [l.strip() for l in first_20_lines if l.strip() and not l.strip().startswith("---") and not l.strip().startswith("title:") and not l.strip().startswith("## Page") and not l.strip().startswith("# PDF Document:")]
        for line in lines_non_empty:
            if line.startswith("# "):
                content_title = line.replace("# ", "").strip()
                break
                
    if content_title:
        title = re.sub(r"\s+", " ", content_title).strip()
        title = title.replace('"', '\\"').strip()
        if title:
            return title
            
    # Fallback to cleaned filename
    title = base_clean.replace("-", " ").replace("_", " ")
    words = title.split()
    cased_words = []
    acronyms = {"bog": "BOG", "ec": "EC", "ug": "UG", "pg": "PG", "bca": "BCA", "bba": "BBA", "llb": "LLB", "coe": "COE", "iqac": "IQAC", "aqar": "AQAR", "tu": "TU", "kle": "KLE", "kletech": "KLE Tech"}
    for w in words:
        w_lower = w.lower()
        if w_lower in acronyms:
            cased_words.append(acronyms[w_lower])
        else:
            cased_words.append(w.capitalize())
    return " ".join(cased_words)

def main():
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    markdown_root = os.path.normpath(os.path.join(workspace_root, "data", "canonical_markdown"))
    
    if not os.path.exists(markdown_root):
        print(f"Error: Markdown root path '{markdown_root}' does not exist.")
        sys.exit(1)
        
    documents_processed = 0
    titles_updated = 0
    headers_removed_count = 0
    footers_removed_count = 0
    page_markers_removed_count = 0
    metadata_updated_count = 0
    error_count = 0
    
    report_details = []
    
    for root, dirs, files in os.walk(markdown_root):
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                rel_path = os.path.relpath(fp, markdown_root)
                rel_path_unix = rel_path.replace(os.sep, "/")
                
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        
                    # Split YAML front matter and body
                    yaml_meta = {}
                    body_text = content
                    if content.strip().startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            yaml_meta = parse_yaml(parts[1])
                            body_text = parts[2]
                            
                    # 1. Update title if needed
                    orig_title = yaml_meta.get("title", "")
                    new_title = improve_title(f, body_text, orig_title)
                    
                    title_changed = False
                    if orig_title != new_title:
                        yaml_meta["title"] = new_title
                        title_changed = True
                        titles_updated += 1
                        
                    # 2. Extract page markers from body
                    # Look for ## Page X or Page X lines
                    page_matches = re.findall(r"## Page\s+(\d+)", body_text)
                    if not page_matches:
                        # Fallback check for "Page X" on a line by itself
                        page_matches = re.findall(r"^Page\s+(\d+)\s*$", body_text, re.MULTILINE)
                        
                    pages_found = [int(p) for p in page_matches]
                    
                    meta_changed = title_changed
                    if pages_found:
                        min_page = min(pages_found)
                        max_page = max(pages_found)
                        # Add page bounds to YAML
                        if yaml_meta.get("page_start") != min_page or yaml_meta.get("page_end") != max_page:
                            yaml_meta["page_start"] = min_page
                            yaml_meta["page_end"] = max_page
                            meta_changed = True
                            metadata_updated_count += 1
                            
                    # Remove H1 placeholder that matches the original "PDF Document: <name>" title
                    orig_h1_pattern = re.compile(r"^# PDF Document:.*$", re.MULTILINE)
                    body_text, h1_removed = orig_h1_pattern.subn("", body_text)
                    
                    # 3. Remove Page Markers and Page numbers in body text
                    # We remove "## Page X" lines and "Page X" lines
                    # We also look for isolated single page numbers within 3 lines of the page headers
                    lines = body_text.splitlines()
                    cleaned_body_lines = []
                    idx = 0
                    
                    while idx < len(lines):
                        line = lines[idx]
                        line_strip = line.strip()
                        
                        # Match page markers: "## Page X" or "Page X" on a line by itself
                        page_marker_match = re.match(r"^## Page\s+(\d+)\s*$", line_strip)
                        if not page_marker_match:
                            page_marker_match = re.match(r"^Page\s+(\d+)\s*$", line_strip)
                            
                        if page_marker_match:
                            page_num = page_marker_match.group(1)
                            page_markers_removed_count += 1
                            
                            # Clean surrounding lines: check next 3 lines for the isolated digit matching page_num
                            for offset in range(1, 4):
                                if idx + offset < len(lines):
                                    next_line = lines[idx + offset].strip()
                                    if next_line == page_num:
                                        # Remove that page number line by setting it empty
                                        lines[idx + offset] = ""
                                        page_markers_removed_count += 1
                                        break
                                        
                            # Skip the page marker line itself
                            idx += 1
                            continue
                            
                        # 4. Remove repetitive PDF artifacts / headers / footers
                        # Scanner footer like FMCD2009 / 2.0
                        if re.match(r"^FMCD2009\s*/\s*2\.0\s*$", line_strip, re.IGNORECASE):
                            headers_removed_count += 1
                            idx += 1
                            continue
                        if re.match(r"^BACK\s*$", line_strip, re.IGNORECASE):
                            footers_removed_count += 1
                            idx += 1
                            continue
                            
                        cleaned_body_lines.append(line)
                        idx += 1
                        
                    polished_body = "\n".join(cleaned_body_lines)
                    
                    # Deduplicate empty lines
                    polished_body = re.sub(r"\n{3,}", "\n\n", polished_body)
                    
                    # Save polished file
                    updated_yaml_text = serialize_yaml(yaml_meta)
                    final_content = updated_yaml_text + "\n" + polished_body.strip() + "\n"
                    
                    with open(fp, "w", encoding="utf-8") as fh:
                        fh.write(final_content)
                        
                    documents_processed += 1
                    report_details.append({
                        "file": rel_path_unix,
                        "title_improved": title_changed,
                        "pages": f"{yaml_meta.get('page_start', '')}-{yaml_meta.get('page_end', '')}" if pages_found else ""
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to polish {rel_path}: {e}")
                    error_count += 1
                    
    # Generate final_polish_report.json
    report_json_path = os.path.join(workspace_root, "final_polish_report.json")
    try:
        with open(report_json_path, "w", encoding="utf-8") as rf:
            json.dump({
                "documents_processed": documents_processed,
                "titles_updated": titles_updated,
                "headers_removed": headers_removed_count,
                "footers_removed": footers_removed_count,
                "page_markers_removed": page_markers_removed_count,
                "metadata_updated": metadata_updated_count,
                "errors": error_count,
                "details": report_details
            }, rf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write JSON report: {e}")
        error_count += 1
        
    print("\n=========================================")
    print("      FINAL POLISH JOB SUMMARY")
    print("=========================================")
    print(f"Documents Processed    : {documents_processed}")
    print(f"Titles Improved        : {titles_updated}")
    print(f"PDF Artifacts Removed  : {headers_removed_count + footers_removed_count + page_markers_removed_count}")
    print(f"Metadata Updated       : {metadata_updated_count}")
    print(f"Errors Encountered     : {error_count}")
    print(f"JSON Report Generated  : {report_json_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
