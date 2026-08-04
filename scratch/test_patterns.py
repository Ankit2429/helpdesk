import re

GREETING_PATTERN = re.compile(
    r"\b(hi+|he+y+|hello+|greetings|good morning|good afternoon|good evening|namaste|namaskara|namaskar|namskara|hi there|hey there|suprabhata)\b",
    re.IGNORECASE,
)

CAMPUS_DOMAIN_PATTERN = re.compile(
    r"\b(principal|vc|vice chancellor|chancellor|dean|hod|director|hostel|mess|canteen|fee|fees|admission|admissions|course|courses|depa?rt?ments?|dept|depts|ise|cse|ece|eee|me|mech|ce|civil|bt|biotech|mba|mca|bca|bba|be|btech|mtech|phd|library|placement|placements|exam|timetable|syllabus|results|building|auditorium|kle|kletech|bvb|campus|hubballi|scholarship|cutoff|eligibility|contact|phone|email|address)\b",
    re.IGNORECASE,
)

tests = [
    ("hii", "GREETING"),
    ("hi", "GREETING"),
    ("hello", "GREETING"),
    ("heyy", "GREETING"),
    ("hey", "GREETING"),
    ("hiiii", "GREETING"),
    ("heyyy", "GREETING"),
    ("HELLO", "GREETING"),
    ("depatments", "CAMPUS"),
    ("departments", "CAMPUS"),
    ("dept", "CAMPUS"),
    ("hostel", "CAMPUS"),
    ("library", "CAMPUS"),
    ("cse", "CAMPUS"),
    ("what are the departments", "CAMPUS"),
    ("show me depatments list", "CAMPUS"),
]

print("Pattern Verification:")
print("-" * 50)
all_pass = True
for text, expected in tests:
    if expected == "GREETING":
        match = bool(GREETING_PATTERN.search(text))
        result = "GREETING" if match else "MISS"
    else:
        match = bool(CAMPUS_DOMAIN_PATTERN.search(text))
        result = "CAMPUS" if match else "MISS"
    status = "PASS" if result == expected else "FAIL"
    print(f'{status}: "{text}" -> {result} (expected {expected})')
    if result != expected:
        all_pass = False

print()
print("All passed!" if all_pass else "SOME TESTS FAILED!")
