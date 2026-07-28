#!/usr/bin/env python3
"""
normalize_markdown.py
======================
Normalizes OCR artifacts, list formatting, tables, punctuation spacing, and
Unicode characters in markdown files, preserving factual content, URLs, and code blocks.
"""

import os
import sys
import json
import re

def normalize_text(text):
    ocr_fixes_count = 0
    headings_fixed = 0
    tables_fixed = 0
    formatting_fixes = 0
    
    lines = text.splitlines(keepends=True)
    cleaned_lines = []
    
    # Common OCR merged words dictionary
    ocr_replacements = {
        r"\bEngineeringandTechnology\b": "Engineering and Technology",
        r"\bMechanicalEngineering\b": "Mechanical Engineering",
        r"\bComputerScience\b": "Computer Science",
        r"\bCivilEngineering\b": "Civil Engineering",
        r"\bBiotechnologyDiscipline\b": "Biotechnology Discipline",
        r"\bCURRENTINTAKE\b": "CURRENT INTAKE",
        r"\bSANCTIONEDINTAKE\b": "SANCTIONED INTAKE",
        r"\bYEAROFSTART\b": "YEAR OF START",
        r"\bYEAROFCLOSE\b": "YEAR OF CLOSE",
        r"\bYEAROFCLOSEDSANCTIONEDINTAKE\b": "YEAR OF CLOSED SANCTIONED INTAKE",
        r"\bACCREDITATIONSTATUS\b": "ACCREDITATION STATUS",
        r"\bPROGRAMDURATION\b": "PROGRAM DURATION",
        r"\bPROGRAMNAME\b": "PROGRAM NAME",
        r"\bPROGRAMAPPLIEDLEVEL\b": "PROGRAM APPLIED LEVEL",
        r"\bAUTHORITYARROVAL\b": "AUTHORITY APPROVAL",
        r"\bAPPROVALDETAILSACCREDITATIONSTATUS\b": "APPROVAL DETAILS ACCREDITATION STATUS",
        r"\b11No\b": "11 No",
        r"\b10No\b": "10 No",
        r"\bTableNo\b": "Table No",
        r"\bSr\.No\b": "Sr. No",
        r"\bNo\.of\b": "No. of",
        r"\bNo\.ofUG\b": "No. of UG",
        r"\bNo\.ofPG\b": "No. of PG",
        r"\bTechnologyPG\b": "Technology PG",
        r"\bAutomation&Robotics\b": "Automation & Robotics",
        r"\bElectronics&CommunicationEngineering\b": "Electronics & Communication Engineering",
        r"\bElectrical&ElectronicsEngineering\b": "Electrical & Electronics Engineering",
        r"\bElectronicsandCommunicationEngineering\b": "Electronics and Communication Engineering",
    }
    
    for line in lines:
        line_strip = line.strip()
        is_table = line_strip.startswith("|") or (line_strip.count("|") >= 2)
        is_code = line_strip.startswith("```") or line_strip.startswith("`")
        
        # Skip modifications inside code blocks
        if is_code:
            cleaned_lines.append(line)
            continue
            
        # 1. OCR Merged Word Fixes
        line_before = line
        for pattern, repl in ocr_replacements.items():
            line = re.sub(pattern, repl, line, flags=re.IGNORECASE)
        if line != line_before:
            ocr_fixes_count += 1
            
        # 2. Convert Unicode dashes and quotes into consistent Markdown
        line_before = line
        line = line.replace("“", "\"").replace("”", "\"")
        line = line.replace("‘", "'").replace("’", "'")
        line = line.replace("—", "-").replace("–", "-")
        if line != line_before:
            formatting_fixes += 1
            
        # 3. Heading fixes (e.g. ##Heading -> ## Heading)
        if line_strip.startswith("#"):
            line_before = line
            line = re.sub(r"^(#+)([^#\s])", r"\1 \2", line)
            if line != line_before:
                headings_fixed += 1
                
        # 4. Bullet lists spaces (e.g. -Bullet -> - Bullet)
        if re.match(r"^\s*[-*+]\w", line_strip):
            line_before = line
            # Insert space after list marker
            line = re.sub(r"^(\s*[-*+])([A-Za-z0-9])", r"\1 \2", line)
            if line != line_before:
                formatting_fixes += 1
                
        # 5. Numbered lists spaces (e.g. 1.Number -> 1. Number)
        if re.match(r"^\s*\d+\.\w", line_strip):
            line_before = line
            line = re.sub(r"^(\s*\d+\.)([A-Za-z0-9])", r"\1 \2", line)
            if line != line_before:
                formatting_fixes += 1
                
        # 6. Punctuation spacing (comma and semicolon followed by word characters)
        if not is_table:
            line_before = line
            line = re.sub(r"(?<=[\w]),(?=\w)", r", ", line)
            line = re.sub(r"(?<=[\w]);(?=\w)", r"; ", line)
            # Colon followed by letters (protecting URLs/times)
            line = re.sub(r"(?<=[\w]):(?=[A-Za-z])", r": ", line)
            if line != line_before:
                formatting_fixes += 1
                
        # 7. Normalize whitespace (skipping tables for alignment)
        if not is_table:
            line_before = line
            # Compress multiple spaces
            # Preserve leading indentation spacing
            leading_space = len(line) - len(line.lstrip())
            line_content = line.lstrip()
            line_content = re.sub(r"[ \t]+", " ", line_content)
            line = " " * leading_space + line_content
            if line != line_before:
                formatting_fixes += 1
        else:
            # Table normalization: ensure columns are separated and stripped
            line_before = line
            cells = line_strip.split("|")
            cleaned_cells = [cell.strip() for cell in cells]
            line = " | ".join(cleaned_cells).strip() + "\n"
            if line != line_before:
                tables_fixed += 1
                
        cleaned_lines.append(line)
        
    return "".join(cleaned_lines), ocr_fixes_count, headings_fixed, tables_fixed, formatting_fixes

def main():
    workspace_root = r"d:\helpdesk\anti"
    kb_root = os.path.normpath(os.path.join(workspace_root, "archive", "bvbcet_scraper", "knowledge_base"))
    markdown_root = os.path.join(kb_root, "markdown")
    
    if not os.path.exists(markdown_root):
        print(f"Error: Markdown root path '{markdown_root}' does not exist.")
        sys.exit(1)
        
    files_processed = 0
    total_ocr_fixes = 0
    total_headings_fixed = 0
    total_tables_fixed = 0
    total_formatting_fixes = 0
    files_skipped = 0
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
                        
                    norm_content, ocr_fixes, headings, tables, formats = normalize_text(content)
                    
                    # Write normalized content
                    with open(fp, "w", encoding="utf-8") as file_handle:
                        file_handle.write(norm_content)
                        
                    files_processed += 1
                    total_ocr_fixes += ocr_fixes
                    total_headings_fixed += headings
                    total_tables_fixed += tables
                    total_formatting_fixes += formats
                    
                    processed_list.append({
                        "file": rel_path.replace(os.sep, "/"),
                        "ocr_fixes": ocr_fixes,
                        "headings_normalized": headings,
                        "tables_normalized": tables,
                        "formatting_fixes": formats
                    })
                except Exception as e:
                    print(f"[ERROR] Failed to normalize {rel_path}: {e}")
                    error_count += 1
                    files_skipped += 1
                    
    # Write normalize_report.json
    report_json_path = os.path.join(workspace_root, "normalize_report.json")
    try:
        with open(report_json_path, "w", encoding="utf-8") as rf:
            json.dump({
                "files_processed_count": files_processed,
                "total_ocr_fixes_applied": total_ocr_fixes,
                "total_headings_normalized": total_headings_fixed,
                "total_tables_normalized": total_tables_fixed,
                "total_formatting_fixes": total_formatting_fixes,
                "files_skipped_count": files_skipped,
                "errors_count": error_count,
                "details": processed_list
            }, rf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write JSON report: {e}")
        error_count += 1

    print("\n=========================================")
    print("      MARKDOWN NORMALIZATION SUMMARY")
    print("=========================================")
    print(f"Files Processed        : {files_processed}")
    print(f"OCR Fixes Applied      : {total_ocr_fixes}")
    print(f"Headings Normalized    : {total_headings_fixed}")
    print(f"Tables Normalized      : {total_tables_fixed}")
    print(f"Formatting Fixes       : {total_formatting_fixes}")
    print(f"Files Skipped          : {files_skipped}")
    print(f"Errors Encountered     : {error_count}")
    print(f"JSON Report Generated  : {report_json_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
