"""Configuration Module for Evaluation Dataset Generator.

Provides dataclasses, category mappings, real-world helpdesk personas,
and natural conversational query templates.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class GeneratorConfig:
    """Configuration options for dataset generator pipeline."""

    input_dir: Path = Path("data/processed_docs")
    output_dir: Path = Path("evaluation/datasets")
    min_questions_per_doc: int = 5
    max_questions_per_doc: int = 20
    words_per_question: int = 80
    dedup_threshold: float = 0.85
    min_answer_length: int = 5
    max_answer_length: int = 500
    overwrite_existing: bool = True
    verbose: bool = False

    # Valid target dataset categories
    categories: Set[str] = field(
        default_factory=lambda: {
            "Admission",
            "Departments",
            "Hostel",
            "Fees",
            "Placement",
            "Navigation",
            "Facilities",
            "Faculty",
            "Misc",
        }
    )

    # Category -> Output dataset filename mapping
    category_file_map: Dict[str, str] = field(
        default_factory=lambda: {
            "Admission": "admission.json",
            "Departments": "departments.json",
            "Hostel": "hostel.json",
            "Fees": "fees.json",
            "Placement": "placement.json",
            "Navigation": "navigation.json",
            "Facilities": "facilities.json",
            "Faculty": "faculty.json",
            "Misc": "misc.json",
        }
    )

    # Real-world helpdesk personas
    personas: List[str] = field(
        default_factory=lambda: [
            "newly admitted student",
            "parent accompanying student",
            "first-time campus visitor",
            "prospective student",
            "guest attending an event",
            "student lost on campus",
            "student visiting another department",
            "student looking for administrative offices",
        ]
    )

    # Category keyword indicators for classification
    category_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "Admission": [
                "admission", "apply", "eligibility", "entrance", "kcet", "comedk",
                "quota", "lateral entry", "counseling", "cut off", "application", "prospectus"
            ],
            "Departments": [
                "department", "computer science", "electronics", "electrical", "mechanical",
                "civil", "biotechnology", "syllabus", "curriculum", "labs", "mca", "mba", "mtech", "btech", "robotics"
            ],
            "Hostel": [
                "hostel", "accommodation", "dormitory", "mess", "warden", "room",
                "boarder", "residence", "curfew", "laundry"
            ],
            "Fees": [
                "fee", "tuition", "payment", "dues", "scholarship", "cost",
                "installment", "refund", "bank", "receipt"
            ],
            "Placement": [
                "placement", "recruiter", "package", "ctc", "internship", "campus drive",
                "career", "hiring", "company", "training", "highest package"
            ],
            "Navigation": [
                "location", "address", "reach", "bus", "train", "airport", "campus map",
                "direction", "gate", "building", "block", "transport", "parking", "auditorium", "canteen", "washroom"
            ],
            "Facilities": [
                "library", "canteen", "sports", "gym", "auditorium", "wifi", "lab",
                "hospital", "bank", "atm", "infrastructure", "incubator", "center of excellence", "cafeteria"
            ],
            "Faculty": [
                "faculty", "professor", "dean", "hod", "staff", "researcher",
                "designation", "contact", "qualification", "publication", "teacher"
            ],
        }
    )
