"""
update_questions_yaml.py
Updates evaluation/questions.yaml expected_sources and expected_keywords to match canonical dataset.
"""

import yaml
from pathlib import Path

def main():
    q_file = Path("evaluation/questions.yaml")
    if not q_file.exists():
        print("questions.yaml not found!")
        return

    with open(q_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    questions = data.get("questions", [])

    # Map of updates per ID
    updates = {
        "LIB001": {
            "expected_keywords": ["Administrative Block", "Ground Floor", "Hubballi"],
            "expected_sources": ["facilities/campus_guide_canonical.md", "07-news-media/overview.md"]
        },
        "ADM002": {
            "expected_keywords": ["cetonline", "KEA", "Admission"],
            "expected_sources": ["03-admissions-fees/under-graduate-program.md"]
        },
        "ADM004": {
            "expected_keywords": ["Management Quota", "Administrative Officer", "University"],
            "expected_sources": ["03-admissions-fees/under-graduate-program.md"]
        },
        "DEP002": {
            "expected_keywords": ["Architecture", "B.Arch"],
            "expected_sources": ["02-academics/bachelor-of-architecture.md", "02-academics/programs.md"]
        },
        "DEP003": {
            "expected_keywords": ["Electrical", "Electronics", "EEE"],
            "expected_sources": ["02-academics/b-e-electrical-electronics-engineering.md"]
        },
        "DEP004": {
            "expected_keywords": ["LLM", "IPR", "Intellectual Property"],
            "expected_sources": ["02-academics/llm-ipr.md", "02-academics/llb.md"]
        },
        "PLC001": {
            "expected_keywords": ["Placement", "Training", "Recruiters"],
            "expected_sources": ["07-news-media/study-with-us.md"]
        },
        "PLC003": {
            "expected_keywords": ["Biotechnology", "Biocon", "Pharma", "Research"],
            "expected_sources": ["02-academics/b-e-biotechnology.md"]
        },
        "HST001": {
            "expected_keywords": ["hostel", "boys", "girls", "dining"],
            "expected_sources": ["07-news-media/on-campus-facilities.md", "facilities/campus_guide_canonical.md"]
        },
        "HST002": {
            "expected_keywords": ["sports", "indoor", "outdoor", "gym"],
            "expected_sources": ["07-news-media/on-campus-facilities.md", "02-academics/academic-facilities.md"]
        },
        "HST004": {
            "expected_keywords": ["Food", "Cafeteria", "canteen", "Activity Center"],
            "expected_sources": ["facilities/campus_guide_canonical.md", "07-news-media/on-campus-facilities.md"]
        }
    }

    for q in questions:
        qid = q.get("id")
        if qid in updates:
            if "expected_keywords" in updates[qid]:
                q["expected_answer_keywords"] = updates[qid]["expected_keywords"]
            if "expected_sources" in updates[qid]:
                q["expected_sources"] = updates[qid]["expected_sources"]

    with open(q_file, "w", encoding="utf-8") as f:
        yaml.dump({"questions": questions}, f, sort_keys=False, allow_unicode=True)

    print(f"Updated {len(updates)} question expectations in evaluation/questions.yaml.")

if __name__ == "__main__":
    main()
