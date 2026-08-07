#!/usr/bin/env python3
"""
generate_metadata.py
====================
Generates and prepends structured YAML front matter for every markdown document
in the knowledge base, exporting statistics in metadata_report.json.
"""

import os
import sys
import json
import re
from datetime import datetime

# Common english stopwords to filter out from keywords
STOPWORDS = {
    "the", "and", "a", "an", "of", "to", "in", "for", "on", "with", "is", "at", 
    "by", "from", "about", "as", "into", "like", "through", "after", "over", 
    "between", "under", "against", "during", "without", "before", "each", "other",
    "some", "such", "than", "its", "our", "your", "their", "this", "that", "these",
    "those", "first", "second", "third", "page", "source", "url", "pdf"
}

def extract_keywords(title, content, headings):
    # Combine title, headings, and split into tokens
    words = []
    # Add title words
    if title:
        words.extend(re.findall(r"\b[A-Za-z]{3,}\b", title.lower()))
    # Add headings words
    for h in headings:
        words.extend(re.findall(r"\b[A-Za-z]{3,}\b", h.lower()))
        
    # Count frequencies of words in content to extract repeated terms
    content_words = re.findall(r"\b[A-Za-z]{4,}\b", content.lower())
    freq = {}
    for w in content_words:
        if w not in STOPWORDS:
            freq[w] = freq.get(w, 0) + 1
            
    # Get top 5 repeated words
    repeated = sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:5]
    words.extend(repeated)
    
    # Unique, non-stopwords keywords
    kw_set = set()
    for w in words:
        if w not in STOPWORDS:
            kw_set.add(w)
            
    return sorted(list(kw_set))[:10]

def extract_aliases(content):
    aliases = []
    content_lower = content.lower()
    
    # Rule 1: HOD / Head of Department
    if "hod" in content_lower or "head of department" in content_lower:
        aliases.append("HOD")
        aliases.append("Head of Department")
        
    # Rule 2: Mechanical Engineering
    if "mechanical engineering" in content_lower:
        aliases.extend(["ME", "Mechanical Dept"])
        
    # Rule 3: Computer Science
    if "computer science" in content_lower:
        aliases.extend(["CSE", "CS"])
        
    # Rule 4: Electronics & Communication
    if "electronics & communication" in content_lower or "electronics and communication" in content_lower:
        aliases.extend(["ECE", "EC"])
        
    # Rule 5: Electrical & Electronics
    if "electrical & electronics" in content_lower or "electrical and electronics" in content_lower:
        aliases.extend(["EEE", "EE"])
        
    # Rule 6: KLE Tech
    if "kle technological university" in content_lower:
        aliases.extend(["KLETech", "KLE Tech"])
        
    # Rule 7: BVB
    if "b.v. bhoomaraddi" in content_lower or "b v bhoomaraddi" in content_lower or "bvbcet" in content_lower:
        aliases.extend(["BVB", "BVBCET"])
        
    # Clean duplicates and preserve order
    seen = set()
    unique_aliases = []
    for a in aliases:
        if a not in seen:
            seen.add(a)
            unique_aliases.append(a)
            
    return unique_aliases

def main():
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    markdown_root = os.path.normpath(os.path.join(workspace_root, "data", "canonical_markdown"))
    
    if not os.path.exists(markdown_root):
        print(f"Error: Markdown root path '{markdown_root}' does not exist.")
        sys.exit(1)
        
    files_processed = 0
    missing_titles = 0
    missing_source_urls = 0
    missing_categories = 0
    error_count = 0
    
    report_details = {}
    
    for root, dirs, files in os.walk(markdown_root):
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                rel_path = os.path.relpath(fp, markdown_root)
                rel_path_unix = rel_path.replace(os.sep, "/")
                
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                        
                    # Rule 7: Never overwrite existing metadata front matter
                    if content.strip().startswith("---"):
                        print(f"[SKIP] {rel_path} already has front matter.")
                        files_processed += 1
                        continue
                        
                    lines = content.splitlines()
                    
                    # 1. Infer title
                    title = ""
                    for line in lines:
                        if line.strip().startswith("# "):
                            title = line.strip().replace("# ", "", 1).replace('"', '\\"')
                            break
                    if not title:
                        missing_titles += 1
                        
                    # 2. Infer Source URL
                    source_url = ""
                    for line in lines:
                        if line.strip().startswith("**Source URL:**"):
                            source_url = line.strip().replace("**Source URL:**", "", 1).strip()
                            break
                        elif line.strip().startswith("**PDF Source:**"):
                            source_url = line.strip().replace("**PDF Source:**", "", 1).strip()
                            break
                    if not source_url:
                        missing_source_urls += 1
                        
                    # 3. Infer category & subcategory from file path
                    parts = rel_path_unix.split("/")
                    category = ""
                    subcategory = ""
                    if len(parts) > 1:
                        category = parts[0]
                    if len(parts) > 2:
                        subcategory = parts[1]
                    else:
                        # Infer subcategory from filename if nested folder is absent
                        # (e.g. academics/programs_*.md subcategory -> programs)
                        fn_no_ext = os.path.splitext(parts[-1])[0]
                        fn_parts = fn_no_ext.split("_")
                        if len(fn_parts) > 0 and fn_parts[0].isalpha() and fn_parts[0] not in ("about", "news", "overview"):
                            subcategory = fn_parts[0]
                            
                    if not category:
                        missing_categories += 1
                        
                    # 4. Infer Document Type
                    content_lower = content.lower()
                    doc_type = "document"
                    if "syllabus" in content_lower or "curriculum" in content_lower:
                        doc_type = "syllabus"
                    elif "time table" in content_lower or "timetable" in content_lower:
                        doc_type = "timetable"
                    elif "notice" in content_lower or "circular" in content_lower:
                        doc_type = "notice"
                    elif "minutes" in content_lower or "meeting" in content_lower:
                        doc_type = "minutes"
                    elif "act" in content_lower:
                        doc_type = "act"
                    elif "statute" in content_lower:
                        doc_type = "statutes"
                    elif "placement" in content_lower or "recruit" in content_lower:
                        doc_type = "brochure"
                        
                    # 5. Infer Department
                    department = ""
                    dept_match = re.search(r"department of ([A-Za-z\s]+)", content, re.IGNORECASE)
                    if dept_match:
                        department = dept_match.group(1).strip().split("\n")[0]
                        # Clean trailing list markup or empty words
                        department = re.sub(r"\s+", " ", department).strip()
                        if len(department) > 50:
                            department = department[:50]
                            
                    # 6. Infer Campus
                    campus = ""
                    if "hubballi" in content_lower or "bhoomaraddi" in content_lower:
                        campus = "Hubballi"
                    elif "belagavi" in content_lower or "sheshgiri" in content_lower:
                        campus = "Belagavi"
                    elif "bengaluru" in content_lower:
                        campus = "Bengaluru"
                        
                    # 7. Extract headings for keyword inference
                    headings = []
                    for line in lines:
                        if line.strip().startswith("## "):
                            headings.append(line.strip().replace("## ", ""))
                            
                    # 8. Keywords and Aliases
                    keywords = extract_keywords(title, content, headings)
                    aliases = extract_aliases(content)
                    
                    # Formatting YAML fields
                    scrape_date = "2026-07-28"
                    last_modified = datetime.now().strftime("%Y-%m-%d")
                    language = "en"
                    
                    yaml_front_matter = (
                        "---\n"
                        f"title: \"{title}\"\n"
                        f"category: \"{category}\"\n"
                        f"subcategory: \"{subcategory}\"\n"
                        f"document_type: \"{doc_type}\"\n"
                        f"department: \"{department}\"\n"
                        f"campus: \"{campus}\"\n"
                        f"source_url: \"{source_url}\"\n"
                        f"scrape_date: \"{scrape_date}\"\n"
                        f"language: \"{language}\"\n"
                        f"keywords: {json.dumps(keywords)}\n"
                        f"aliases: {json.dumps(aliases)}\n"
                        f"last_modified: \"{last_modified}\"\n"
                        "---\n"
                    )
                    
                    # Prepend metadata to the file
                    new_content = yaml_front_matter + content
                    with open(fp, "w", encoding="utf-8") as fh:
                        fh.write(new_content)
                        
                    files_processed += 1
                    report_details[rel_path_unix] = {
                        "title": title,
                        "category": category,
                        "subcategory": subcategory,
                        "document_type": doc_type,
                        "department": department,
                        "campus": campus,
                        "keywords": keywords,
                        "aliases": aliases
                    }
                except Exception as e:
                    print(f"[ERROR] Failed to generate metadata for {rel_path}: {e}")
                    error_count += 1
                    
    # Write metadata_report.json
    report_json_path = os.path.join(workspace_root, "metadata_report.json")
    try:
        with open(report_json_path, "w", encoding="utf-8") as rf:
            json.dump({
                "files_processed_count": files_processed,
                "missing_titles_count": missing_titles,
                "missing_source_urls_count": missing_source_urls,
                "missing_categories_count": missing_categories,
                "errors_count": error_count,
                "metadata_generated": report_details
            }, rf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write report: {e}")
        error_count += 1
        
    print("\n=========================================")
    print("      METADATA GENERATION SUMMARY")
    print("=========================================")
    print(f"Files Processed        : {files_processed}")
    print(f"Missing Titles         : {missing_titles}")
    print(f"Missing Source URLs    : {missing_source_urls}")
    print(f"Missing Categories     : {missing_categories}")
    print(f"Errors Encountered     : {error_count}")
    print(f"JSON Report Generated  : {report_json_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
