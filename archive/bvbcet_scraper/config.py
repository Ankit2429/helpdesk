"""Central Configuration for BVBCET / KLE Tech Campus Knowledge Base Scraper Pipeline."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Scope & Domains
# ---------------------------------------------------------------------------
START_URL = "https://www.kletech.ac.in/hubballi/"
SEED_URLS = [
    "https://www.kletech.ac.in/hubballi/",
]

ALLOWED_DOMAINS = {
    "kletech.ac.in",
    "www.kletech.ac.in",
    "bvb.edu",
    "www.bvb.edu",
}

# Excluded URL fragments & external platforms
SKIP_URL_PATTERNS = [
    "wp-login", "wp-admin", "?share=", "action=login", "mailto:", "tel:",
    "javascript:", "#", "facebook.com", "twitter.com", "instagram.com",
    "linkedin.com", "youtube.com", "google.com/maps", "maps.google",
    "pinterest.com", "whatsapp.com",
]

# ---------------------------------------------------------------------------
# Crawl & HTTP Options
# ---------------------------------------------------------------------------
USER_AGENT = "BVBCET-KLETech-KnowledgeBaseBot/2.0 (+offline campus helpdesk RAG pipeline; respects robots.txt)"
REQUEST_TIMEOUT = 25
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.5
MAX_WORKERS = 5
MAX_PAGES = 3000
RESPECT_ROBOTS_TXT = True

# ---------------------------------------------------------------------------
# Output Directory Structure
# ---------------------------------------------------------------------------
OUTPUT_ROOT = Path("knowledge_base")
MARKDOWN_DIR = OUTPUT_ROOT / "markdown"
PDF_DIR = OUTPUT_ROOT / "pdf"
METADATA_DIR = OUTPUT_ROOT / "metadata"
LOGS_DIR = OUTPUT_ROOT / "logs"

# Categories
CATEGORIES = [
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

# Ensure category directories exist
for cat in CATEGORIES:
    (MARKDOWN_DIR / cat).mkdir(parents=True, exist_ok=True)

PDF_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# File Locations for State and Logging
# ---------------------------------------------------------------------------
METADATA_FILE = METADATA_DIR / "metadata.json"
STATE_FILE = LOGS_DIR / "state.json"
CRAWL_LOG_FILE = LOGS_DIR / "crawl.log"
FAILED_PAGES_LOG = LOGS_DIR / "failed_pages.log"
PDF_DOWNLOAD_LOG = LOGS_DIR / "pdf_download.log"
STATISTICS_FILE = LOGS_DIR / "statistics.json"

# ---------------------------------------------------------------------------
# Classification Rules (URL/title keywords -> Category)
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
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
