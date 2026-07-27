"""Category definitions and classification rule mappings."""

# 18 Standard Target Categories
CATEGORIES: list[str] = [
    "about",
    "admissions",
    "academics",
    "departments",
    "placements",
    "faculty",
    "research",
    "infrastructure",
    "library",
    "hostel",
    "transport",
    "examination",
    "downloads",
    "notices",
    "events",
    "gallery",
    "contact",
    "miscellaneous",
]

# Classification Rules: (keyword_list, category_name)
CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["about", "overview", "history", "founder", "kle-society", "chancellor", "vice-chancellor", "leadership"], "about"),
    (["admission", "apply", "kcet", "comedk", "pgcet", "quota", "eligibility", "fee-structure", "prospectus"], "admissions"),
    (["academic", "program", "course", "curriculum", "syllabus", "undergraduate", "postgraduate", "phd", "btech", "mtech"], "academics"),
    (["department", "computer-science", "information-science", "electronics", "electrical", "civil", "mechanical", "biotech", "automation", "school-of-"], "departments"),
    (["placement", "recruiter", "internship", "career", "salary", "placement-statistics"], "placements"),
    (["faculty", "professor", "staff", "teacher", "head-of-department", "hod"], "faculty"),
    (["research", "publication", "patent", "journal", "r-and-d", "project", "consultancy"], "research"),
    (["infrastructure", "campus", "building", "auditorium", "lab", "laboratory", "canteen", "cafeteria", "sports", "gym"], "infrastructure"),
    (["library", "digital-library", "e-resources", "journals", "book"], "library"),
    (["hostel", "accommodation", "dormitory", "residence", "mess"], "hostel"),
    (["transport", "bus", "route", "vehicle", "commute"], "transport"),
    (["examination", "exam", "grade", "result", "revaluation", "timetable", "evaluations"], "examination"),
    (["download", "form", "brochure", "circular", "policy", "handbook", "rules"], "downloads"),
    (["notice", "announcement", "news", "update"], "notices"),
    (["event", "workshop", "seminar", "conference", "fest", "hackathon", "webinar"], "events"),
    (["gallery", "photo", "video", "album", "picture"], "gallery"),
    (["contact", "address", "reach-us", "directory", "map", "location", "phone", "email"], "contact"),
]
