"""Query Normalization Pipeline for the Sparky Campus Helpdesk.

Executes BEFORE IntentRouter to transform informal, misspelled, or noisy user
input into a clean, canonical form that downstream components can reliably match.

Pipeline (applied in order):
    1. Lowercase
    2. Trim whitespace (leading/trailing) + collapse internal runs
    3. Remove repeated punctuation  (hostel??? → hostel)
    4. Collapse repeated letters in conversational greetings only
       (hiiiii → hi, heyyy → hey, helloooo → hello)
    5. Spelling correction  (depatments → departments)
    6. Synonym expansion    (branch → departments, mess → hostel)

Usage::

    from campus_helpdesk.services.query_normalizer import normalize_query

    clean = normalize_query("  HOSTEL!!!  ")   # → "hostel"
    clean = normalize_query("depatments")       # → "departments"
    clean = normalize_query("branch")           # → "departments"

The module is intentionally pure-Python with no external dependencies.
All dictionaries live in one place so they are easy to maintain.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1.  Greeting tokens whose repeated letters should be collapsed.
#     Only these words (and their repetition-distorted forms) are modified.
#     Normal English words are NEVER touched.
# ---------------------------------------------------------------------------
_GREETING_COLLAPSE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # hi / hii / hiiii  →  hi
    (re.compile(r"\bhi{2,}\b", re.IGNORECASE), "hi"),
    # he+y+  → hey  (heyy, heyyy, heeey, heeeyyy …)
    (re.compile(r"\bhe+y+\b", re.IGNORECASE), "hey"),
    # hello+  → hello  (helloo, helloooo …)
    (re.compile(r"\bhello{2,}\b", re.IGNORECASE), "hello"),
    # helo / helloo – common one-l variant
    (re.compile(r"\bhelo+\b", re.IGNORECASE), "hello"),
    # byee / byeee  → bye
    (re.compile(r"\bbye{2,}\b", re.IGNORECASE), "bye"),
    # okk / okkk  → ok
    (re.compile(r"\bok{2,}\b", re.IGNORECASE), "ok"),
]

# ---------------------------------------------------------------------------
# 2.  Spelling-correction dictionary.
#     Key   = misspelled word (lower-case, no punctuation)
#     Value = correct word / phrase
#
#     Rules:
#       - Keys must be lowercase and contain NO regex metacharacters.
#       - Values are substituted as-is (lower-case).
#       - Add new entries here; no other code needs to change.
# ---------------------------------------------------------------------------
_SPELLING_CORRECTIONS: dict[str, str] = {
    # --- departments / academic ---
    "depatments": "departments",
    "depatment": "department",
    "departements": "departments",
    "deparments": "departments",
    "deptartments": "departments",
    "deptartment": "department",
    "deprtments": "departments",
    "deprtment": "department",
    # --- hostel ---
    "hostell": "hostel",
    "hotsel": "hostel",
    "hosel": "hostel",
    "hostle": "hostel",
    # --- library ---
    "libary": "library",
    "libarary": "library",
    "libreary": "library",
    "librery": "library",
    "libery": "library",
    # --- scholarship ---
    "scholership": "scholarship",
    "scolarship": "scholarship",
    "scholrship": "scholarship",
    "scholarshp": "scholarship",
    # --- admission ---
    "admision": "admission",
    "addmission": "admission",
    "admissions": "admissions",   # already correct – keep as no-op guard
    # --- timetable ---
    "timtable": "timetable",
    "timetabel": "timetable",
    "timetable": "timetable",     # no-op guard
    "time table": "timetable",    # phrase handled via internal-space collapse
    # --- canteen ---
    "canteenn": "canteen",
    "cantten": "canteen",
    # --- placement ---
    "placment": "placement",
    "placeemnt": "placement",
    "placments": "placements",
    # --- chancellor ---
    "chancelor": "chancellor",
    "chancelors": "chancellors",
    # --- college ---
    "colage": "college",
    "callege": "college",
    # --- miscellaneous ---
    "vce": "vice",
    "qota": "quota",
    "whre": "where",
    "mes": "mess",
    "tabel": "table",
    "libery": "library",
    "coleg": "college",
    "admisssion": "admission",
    "schlarship": "scholarship",
    "facilties": "facilities",
    "facilites": "facilities",
}

# Pre-compile spelling-correction patterns once at module load.
# Each entry becomes an anchored whole-word pattern so "dept" inside
# "department" is not accidentally changed.
_COMPILED_SPELL: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b" + re.escape(wrong) + r"\b", re.IGNORECASE), correct)
    for wrong, correct in _SPELLING_CORRECTIONS.items()
]

# ---------------------------------------------------------------------------
# 3.  Synonym / alias mapping.
#     Key   = alias phrase (lower-case; multi-word phrases supported)
#     Value = canonical term understood by Intent Router & RAG Pipeline
#
#     Rules:
#       - Keys must be lowercase.
#       - Longer phrases are matched before shorter ones (dict preserves
#         insertion order; we sort by length descending at compile time).
#       - Add new entries here only.
# ---------------------------------------------------------------------------
_SYNONYM_MAP: dict[str, str] = {
    # --- departments ---
    "branches": "departments",
    "branch": "departments",
    "depts": "departments",
    "dept": "departments",
    "department": "departments",
    # --- hostel ---
    "mess": "hostel",
    "dormitory": "hostel",
    "dorm": "hostel",
    "pg": "hostel",
    # --- library timing ---
    "library timing": "library hours",
    "library timings": "library hours",
    "library time": "library hours",
    "library open time": "library hours",
    # --- fee structure ---
    "fees structure": "fee structure",
    "fees details": "fee structure",
    "fee details": "fee structure",
    "fee amount": "fee structure",
    "fees amount": "fee structure",
    "how much fees": "fee structure",
    "how much fee": "fee structure",
    # --- canteen ---
    "canteen food": "canteen",
    "cafeteria": "canteen",
    "food court": "canteen",
    # --- placement ---
    "job placement": "placement",
    "campus recruitment": "placement",
    "campus placements": "placements",
    # --- timetable ---
    "exam schedule": "timetable",
    "class schedule": "timetable",
    "lecture schedule": "timetable",
    "schedule": "timetable",
    # --- admission ---
    "apply": "admission",
    "how to join": "admission",
    "how to get in": "admission",
    "joining": "admission",
}

# Pre-compile synonym patterns (longest key first to avoid partial shadowing).
_COMPILED_SYNONYMS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE), canonical)
    for alias, canonical in sorted(_SYNONYM_MAP.items(), key=lambda x: -len(x[0]))
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_query(text: str, *, debug: bool = False) -> str:
    """Normalize raw user input into a clean, canonical query string.

    Args:
        text:  Raw user input exactly as received from the UI.
        debug: When True, each transformation step is logged at DEBUG level.
               This is automatically enabled when the application's
               ``Settings.debug`` flag is set; callers may also pass it
               explicitly for testing.

    Returns:
        A normalized string safe to pass to IntentRouter.
    """
    if not isinstance(text, str):
        return ""

    original = text

    # ------------------------------------------------------------------
    # Step 1: Lowercase
    # ------------------------------------------------------------------
    step = text.lower()

    # ------------------------------------------------------------------
    # Step 2: Trim + collapse internal whitespace runs
    #         "   library     timings   "  →  "library timings"
    # ------------------------------------------------------------------
    step = re.sub(r"\s+", " ", step).strip()

    # ------------------------------------------------------------------
    # Step 3: Remove trailing/repeated punctuation
    #         "hostel???"  → "hostel"
    #         "hello!!!!"  → "hello"
    #         "HOSTEL!!!"  → "hostel" (already lower-cased)
    # ------------------------------------------------------------------
    # Remove one or more consecutive punctuation characters at end-of-string
    step = re.sub(r"[!?.,:;]+$", "", step).strip()
    # Also collapse mid-string repeated punctuation (e.g., "hostel???fees")
    step = re.sub(r"([!?.,:;])\1+", r"\1", step)

    after_punct = step  # checkpoint for logging

    # ------------------------------------------------------------------
    # Step 4: Collapse repeated letters for greeting words ONLY
    # ------------------------------------------------------------------
    after_spell_before_greet = step  # will set below; keep for logging order
    for pattern, replacement in _GREETING_COLLAPSE_PATTERNS:
        step = pattern.sub(replacement, step)

    after_greet = step  # checkpoint for logging

    # ------------------------------------------------------------------
    # Step 5: Spelling correction
    # ------------------------------------------------------------------
    after_spell_before = step
    for pattern, correct in _COMPILED_SPELL:
        step = pattern.sub(correct, step)

    after_spell = step  # checkpoint for logging

    # ------------------------------------------------------------------
    # Step 6: Synonym expansion
    # ------------------------------------------------------------------
    after_synonym_before = step
    for pattern, canonical in _COMPILED_SYNONYMS:
        step = pattern.sub(canonical, step)

    final = step

    # ------------------------------------------------------------------
    # Debug logging
    # ------------------------------------------------------------------
    if debug or logger.isEnabledFor(logging.DEBUG):
        if final != original:
            logger.debug(
                "[QueryNormalizer]\n"
                "  Original Query   : %r\n"
                "  After Punct      : %r\n"
                "  Greeting Collapse: %r\n"
                "  Spell Corrected  : %r\n"
                "  Synonym Applied  : %r\n"
                "  Final Query      : %r",
                original,
                after_punct,
                after_greet,
                after_spell,
                final,
                final,
            )

    return final


# ---------------------------------------------------------------------------
# Convenience helpers for external extension
# ---------------------------------------------------------------------------


def add_spelling_correction(wrong: str, correct: str) -> None:
    """Register an additional spelling correction at runtime.

    Args:
        wrong:   Misspelled word (lower-case, no regex metacharacters).
        correct: Correct replacement word/phrase.

    The new entry takes effect immediately for all subsequent calls to
    :func:`normalize_query`.  This API exists for plugin/extension use;
    prefer editing ``_SPELLING_CORRECTIONS`` for permanent changes.
    """
    _SPELLING_CORRECTIONS[wrong.lower()] = correct.lower()
    pattern = re.compile(r"\b" + re.escape(wrong.lower()) + r"\b", re.IGNORECASE)
    _COMPILED_SPELL.append((pattern, correct.lower()))


def add_synonym(alias: str, canonical: str) -> None:
    """Register an additional synonym mapping at runtime.

    Args:
        alias:     The user-facing alias phrase (lower-case).
        canonical: The preferred canonical term.
    """
    _SYNONYM_MAP[alias.lower()] = canonical.lower()
    pattern = re.compile(r"\b" + re.escape(alias.lower()) + r"\b", re.IGNORECASE)
    _COMPILED_SYNONYMS.insert(0, (pattern, canonical.lower()))
