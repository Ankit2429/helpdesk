import os
import re
from pathlib import Path
import json

canonical_dir = Path("data/canonical_markdown")
all_files = list(canonical_dir.rglob("*.md"))

low_quality_ocr = []
broken_markdown = []
oversized_chunks = []
missing_entities = {
    "principal": True,
    "vice_chancellor": True,
    "registrar": True,
    "hostel": True,
    "placements": True,
    "fee_structure": True,
    "scholarships": True,
    "academic_calendar": True,
    "exam_schedules": True,
    "campus_map": True,
    "office_contacts": True,
    "student_handbook": True,
    "research": True
}

# Scan each file
for file_path in all_files:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    rel_path = file_path.relative_to(canonical_dir).as_posix()
    
    # 1. Low quality OCR detection (high ratio of non-standard characters/garbage symbols)
    non_alphanum = len(re.findall(r"[^a-zA-Z0-9\s.,;:!?()'-]", content))
    total_chars = len(content)
    if total_chars > 0 and (non_alphanum / total_chars) > 0.15:
        low_quality_ocr.append(rel_path)
        
    # 2. Broken markdown (unclosed brackets/parentheses for links, broken headings)
    if len(re.findall(r"\[[^\]]*$", content, re.MULTILINE)) > 0 or len(re.findall(r"\([^)]*$", content, re.MULTILINE)) > 0:
        broken_markdown.append(rel_path)
        
    # 3. Oversized chunks potential (large paragraphs without headings)
    paragraphs = content.split("\n\n")
    for p in paragraphs:
        word_count = len(p.split())
        if word_count > 600:
            oversized_chunks.append((rel_path, word_count))
            break
            
    # 4. Detect entity presence
    content_lower = content.lower()
    if "principal" in content_lower:
        missing_entities["principal"] = False
    if "vice chancellor" in content_lower or "vice-chancellor" in content_lower or " vc " in content_lower:
        missing_entities["vice_chancellor"] = False
    if "registrar" in content_lower:
        missing_entities["registrar"] = False
    if "hostel" in content_lower:
        missing_entities["hostel"] = False
    if "placement" in content_lower:
        missing_entities["placements"] = False
    if "fee" in content_lower and ("structure" in content_lower or "tuition" in content_lower):
        missing_entities["fee_structure"] = False
    if "scholarship" in content_lower or "financial aid" in content_lower:
        missing_entities["scholarships"] = False
    if "academic calendar" in content_lower or "calendar" in content_lower:
        missing_entities["academic_calendar"] = False
    if "exam schedule" in content_lower or "examination timetable" in content_lower or "timetable" in content_lower:
        missing_entities["exam_schedules"] = False
    if "map" in content_lower or "coordinates" in content_lower:
        missing_entities["campus_map"] = False
    if "office contact" in content_lower or "phone directory" in content_lower or "intercom" in content_lower:
        missing_entities["office_contacts"] = False
    if "handbook" in content_lower or "student manual" in content_lower:
        missing_entities["student_handbook"] = False
    if "research" in content_lower or "publications" in content_lower:
        missing_entities["research"] = False

print(f"Low-quality OCR files: {len(low_quality_ocr)}")
print(f"Broken markdown files: {len(broken_markdown)}")
print(f"Files with oversized paragraphs: {len(oversized_chunks)}")
print("Missing entities check:")
for k, v in missing_entities.items():
    print(f"  {k}: {'MISSING' if v else 'PRESENT'}")

with open("scratch/gaps_audit.json", "w", encoding="utf-8") as f:
    json.dump({
        "low_quality_ocr": low_quality_ocr,
        "broken_markdown": broken_markdown,
        "oversized_chunks": oversized_chunks,
        "missing_entities": missing_entities
    }, f, indent=2)
