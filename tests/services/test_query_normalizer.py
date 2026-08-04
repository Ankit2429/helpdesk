"""Unit tests for campus_helpdesk.services.query_normalizer.

Tests cover every transformation step in the pipeline:
  1. Lowercase
  2. Whitespace trim / collapse
  3. Repeated punctuation removal
  4. Greeting letter collapse  (hiii→hi, heyyy→hey, helloooo→hello)
  5. Spelling corrections
  6. Synonym mappings
  7. Composed / end-to-end examples matching the specification
"""

import pytest
from campus_helpdesk.services.query_normalizer import normalize_query


# ---------------------------------------------------------------------------
# Step 1 – Lowercase
# ---------------------------------------------------------------------------
class TestLowercase:
    def test_all_caps(self):
        assert normalize_query("HOSTEL") == "hostel"

    def test_mixed_case(self):
        assert normalize_query("Library") == "library"

    def test_already_lower(self):
        assert normalize_query("departments") == "departments"


# ---------------------------------------------------------------------------
# Step 2 – Whitespace trim / collapse
# ---------------------------------------------------------------------------
class TestWhitespace:
    def test_leading_trailing(self):
        assert normalize_query("   hostel   ") == "hostel"

    def test_internal_runs(self):
        assert normalize_query("cse     department") == "cse departments"

    def test_leading_trailing_and_internal(self):
        assert normalize_query("   cse     department   ") == "cse departments"

    def test_tab_and_newline(self):
        assert normalize_query("\tcse\ndepartment\n") == "cse departments"


# ---------------------------------------------------------------------------
# Step 3 – Repeated / trailing punctuation removal
# ---------------------------------------------------------------------------
class TestPunctuation:
    def test_question_marks(self):
        assert normalize_query("fees???") == "fees"

    def test_exclamation_marks(self):
        assert normalize_query("HOSTEL!!!") == "hostel"

    def test_hello_exclamation(self):
        # punctuation removed; greeting still valid after normalization
        assert normalize_query("hello!!!!") == "hello"

    def test_mixed_punct(self):
        assert normalize_query("hostel?!") == "hostel"

    def test_single_punct_preserved_mid_string(self):
        # single ? mid-string is kept (not duplicated)
        result = normalize_query("fees?library")
        assert "?" in result  # mid-string single punct retained

    def test_no_punct(self):
        assert normalize_query("hostel") == "hostel"


# ---------------------------------------------------------------------------
# Step 4 – Greeting letter collapse
# ---------------------------------------------------------------------------
class TestGreetingCollapse:
    # hi variants
    def test_hii(self):
        assert normalize_query("hii") == "hi"

    def test_hiii(self):
        assert normalize_query("hiii") == "hi"

    def test_hiiii(self):
        assert normalize_query("hiiii") == "hi"

    def test_hi_unchanged(self):
        assert normalize_query("hi") == "hi"

    # hey variants
    def test_heyy(self):
        assert normalize_query("heyy") == "hey"

    def test_heyyyy(self):
        assert normalize_query("heyyyy") == "hey"

    def test_hey_unchanged(self):
        assert normalize_query("hey") == "hey"

    def test_heey(self):
        assert normalize_query("heey") == "hey"

    # hello variants
    def test_helloo(self):
        assert normalize_query("helloo") == "hello"

    def test_helloooo(self):
        assert normalize_query("helloooo") == "hello"

    def test_hello_unchanged(self):
        assert normalize_query("hello") == "hello"

    # normal words are NOT collapsed
    def test_normal_word_balloon_unchanged(self):
        """'balloon' must NOT be collapsed to 'ballon'."""
        assert normalize_query("balloon") == "balloon"

    def test_normal_word_school_unchanged(self):
        assert normalize_query("school") == "school"

    def test_normal_word_fee_unchanged(self):
        assert normalize_query("fee") == "fee"


# ---------------------------------------------------------------------------
# Step 5 – Spelling corrections
# ---------------------------------------------------------------------------
class TestSpellingCorrection:
    def test_depatments(self):
        assert normalize_query("depatments") == "departments"

    def test_hostell(self):
        assert normalize_query("hostell") == "hostel"

    def test_libary(self):
        assert normalize_query("libary") == "library"

    def test_scholership(self):
        assert normalize_query("scholership") == "scholarship"

    def test_admision(self):
        assert normalize_query("admision") == "admission"

    def test_timtable(self):
        assert normalize_query("timtable") == "timetable"

    def test_deprtments(self):
        assert normalize_query("deprtments") == "departments"

    def test_hostle(self):
        assert normalize_query("hostle") == "hostel"

    def test_placment(self):
        assert normalize_query("placment") == "placement"

    def test_chancelor(self):
        assert normalize_query("chancelor") == "chancellor"

    # Correct spellings are NOT modified
    def test_correct_spelling_passthrough(self):
        assert normalize_query("departments") == "departments"
        assert normalize_query("hostel") == "hostel"
        assert normalize_query("library") == "library"


# ---------------------------------------------------------------------------
# Step 6 – Synonym mapping
# ---------------------------------------------------------------------------
class TestSynonymMapping:
    def test_dept_to_departments(self):
        assert normalize_query("dept") == "departments"

    def test_depts_to_departments(self):
        assert normalize_query("depts") == "departments"

    def test_department_to_departments(self):
        assert normalize_query("department") == "departments"

    def test_branch_to_departments(self):
        assert normalize_query("branch") == "departments"

    def test_branches_to_departments(self):
        assert normalize_query("branches") == "departments"

    def test_mess_to_hostel(self):
        assert normalize_query("mess") == "hostel"

    def test_library_timing_phrase(self):
        assert normalize_query("library timing") == "library hours"

    def test_library_timings_phrase(self):
        assert normalize_query("library timings") == "library hours"

    def test_fees_structure_to_fee_structure(self):
        assert normalize_query("fees structure") == "fee structure"

    def test_cafeteria_to_canteen(self):
        assert normalize_query("cafeteria") == "canteen"

    def test_canteen_food_to_canteen(self):
        assert normalize_query("canteen food") == "canteen"

    def test_exam_schedule_to_timetable(self):
        assert normalize_query("exam schedule") == "timetable"


# ---------------------------------------------------------------------------
# Specification examples  (end-to-end)
# ---------------------------------------------------------------------------
class TestSpecificationExamples:
    """Verify every example listed in the task specification."""

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("hii", "hi"),
            ("heyyyy", "hey"),
            ("HOSTEL!!!", "hostel"),
            ("depatments", "departments"),
            ("hostell", "hostel"),
            ("dept", "departments"),
            ("branch", "departments"),
            ("library timing", "library hours"),
            # Combined: uppercase + repeated punct + spelling
            ("DEPATMENTS???", "departments"),
            # Combined: mixed case + extra spaces + trailing punct
            ("  Library   Timings  ", "library hours"),
            # Combined: greeting + exclamation
            ("heyyyy!", "hey"),
            # Combined: misspell + trailing punct
            ("hostell!!", "hostel"),
        ],
    )
    def test_spec_example(self, raw: str, expected: str):
        assert normalize_query(raw) == expected


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestEdgeCases:
    def test_empty_string(self):
        assert normalize_query("") == ""

    def test_whitespace_only(self):
        assert normalize_query("   ") == ""

    def test_non_string_returns_empty(self):
        assert normalize_query(None) == ""  # type: ignore[arg-type]

    def test_single_character(self):
        assert normalize_query("a") == "a"

    def test_number_passthrough(self):
        assert normalize_query("123") == "123"

    def test_long_query_unchanged(self):
        long = "what is the fee structure for cse department at kle tech"
        expected = "what is the fee structure for cse departments at kle tech"
        assert normalize_query(long) == expected

    def test_idempotent(self):
        """Running normalizer twice produces the same result."""
        raw = "  HOSTELL!!  "
        once = normalize_query(raw)
        twice = normalize_query(once)
        assert once == twice
