import os
import re
import shutil
from pathlib import Path
import yaml  # PyYAML is installed in the venv

source_dir = Path("archive/bvbcet_scraper/knowledge_base/markdown_backup")
target_dir = Path("data/canonical_markdown")

# Recreate canonical dir cleanly
if target_dir.exists():
    shutil.rmtree(target_dir)
target_dir.mkdir(parents=True, exist_ok=True)

categories = [
    "academic", "departments", "faculty", "hostel", "placements", 
    "scholarships", "clubs", "campus", "research", "administration", 
    "circulars", "timetables", "facilities"
]

for cat in categories:
    (target_dir / cat).mkdir(parents=True, exist_ok=True)

# Helper to clean filenames (remove random hex suffix and leading number/code prefixes)
hex_suffix_pat = re.compile(r"_[a-f0-9]{6}$")
prefix_pat = re.compile(r"^\d+[a-zA-Z]+_")

def clean_filename(name: str) -> str:
    stem = name[:-3] if name.endswith(".md") else name
    # Remove hex suffix
    stem = hex_suffix_pat.sub("", stem)
    # Remove leading numbering/source prefixes (e.g. 19krf_ or 265rkf_)
    stem = prefix_pat.sub("", stem)
    # Remove redundant hashes or characters
    stem = stem.strip("_").lower()
    return f"{stem}.md"

# Classification rules based on original path, content keywords, etc.
def classify_file(original_rel_path: str, content: str) -> str:
    path_lower = original_rel_path.lower()
    content_lower = content.lower()
    
    # 1. timetables
    if "timetable" in path_lower or "time_table" in path_lower or "time table" in content_lower:
        if "exam" in path_lower or "exam" in content_lower or "esa" in content_lower:
            return "timetables"
        return "timetables"
        
    # 2. faculty
    if "faculty" in path_lower or "faculty_list" in path_lower:
        return "faculty"
        
    # 3. departments
    if "departments" in path_lower or "department of" in content_lower:
        return "departments"
        
    # 4. placements
    if "placement" in path_lower or "recruiters" in path_lower or "hiring" in content_lower or "placement brochure" in content_lower:
        return "placements"
        
    # 5. hostel
    if "hostel" in path_lower or "mess" in content_lower or "hostel facilities" in content_lower:
        return "hostel"
        
    # 6. scholarships
    if "scholarship" in path_lower or "financial aid" in content_lower or "fee concession" in content_lower:
        return "scholarships"
        
    # 7. research
    if "research" in path_lower or "publications" in content_lower or "patents" in content_lower:
        return "research"
        
    # 8. clubs
    if "club" in path_lower or "society" in path_lower or "gymkhana" in path_lower or "sports" in path_lower:
        return "clubs"
        
    # 9. facilities
    if "library" in path_lower or "canteen" in path_lower or "cafeteria" in path_lower or "facilities" in path_lower or "infrastructure" in path_lower:
        return "facilities"
        
    # 10. circulars & notices
    if "notice" in path_lower or "circular" in path_lower or "announcements" in path_lower:
        return "circulars"
        
    # 11. academic
    if "academic" in path_lower or "calendar" in path_lower or "syllabus" in content_lower or "curriculum" in content_lower or "admission" in path_lower:
        return "academic"
        
    # 12. administration
    if "governance" in path_lower or "board" in content_lower or "act" in path_lower or "governor" in content_lower or "registrar" in content_lower:
        return "administration"
        
    # 13. campus (fallback)
    return "campus"

# Infer metadata attributes from content
def infer_metadata(category: str, filename: str, content: str) -> dict:
    title = "Untitled"
    heading_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if heading_match:
        title = heading_match.group(1).strip()
    else:
        title = filename[:-3].replace("_", " ").title()
        
    doc_type = "information"
    if "policy" in content.lower() or "regulations" in content.lower():
        doc_type = "policy"
    elif "list" in content.lower() or "faculty" in category:
        doc_type = "list"
    elif "notice" in category or "circular" in category:
        doc_type = "notice"
    elif "timetable" in category:
        doc_type = "timetable"
        
    dept = "General"
    depts = ["Biotechnology", "Computer Science", "Information Science", "Civil Engineering", "Mechanical Engineering", "Electronics", "Electrical", "Architecture"]
    for d in depts:
        if d.lower() in content.lower():
            dept = d
            break
            
    keywords = []
    kw_candidates = ["admissions", "syllabus", "fees", "hostel", "placements", "recruiters", "exams", "canteen", "library", "scholarships", "board", "timings"]
    for kw in kw_candidates:
        if kw in content.lower():
            keywords.append(kw)
            
    return {
        "title": title,
        "document_type": doc_type,
        "department": dept,
        "category": category,
        "date": "2026-08-04",
        "keywords": ", ".join(keywords) if keywords else "campus",
        "language": "en",
        "version": "1.0"
    }

# Process and copy
all_source_files = list(source_dir.rglob("*.md"))
print(f"Ingesting and organizing {len(all_source_files)} files...")

seen_dest_names = set()

for file_path in all_source_files:
    content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        continue
        
    rel_path = file_path.relative_to(source_dir).as_posix()
    cat = classify_file(rel_path, content)
    clean_name = clean_filename(file_path.name)
    
    # Avoid collisions
    dest_path = target_dir / cat / clean_name
    if dest_path.as_posix() in seen_dest_names:
        stem = clean_name[:-3]
        clean_name = f"{stem}_alt.md"
        dest_path = target_dir / cat / clean_name
        
    seen_dest_names.add(dest_path.as_posix())
    
    # Get metadata
    meta = infer_metadata(cat, clean_name, content)
    meta["source"] = rel_path
    
    # Prepend frontmatter
    frontmatter_lines = ["---"]
    for k, v in sorted(meta.items()):
        frontmatter_lines.append(f"{k}: {v}")
    frontmatter_lines.append("---")
    frontmatter_str = "\n".join(frontmatter_lines)
    
    final_content = f"{frontmatter_str}\n\n{content}"
    dest_path.write_text(final_content, encoding="utf-8")

print("Reorganization and metadata injection completed.")
