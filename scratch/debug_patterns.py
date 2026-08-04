import re

CAMPUS_DOMAIN_PATTERN = re.compile(
    r"\b(principal|vc|vice chancellor|chancellor|dean|hod|director|hostel|mess|canteen|fee|fees|admission|admissions|course|courses|departments?|depatments?|dept|depts|ise|cse|ece|eee|me|mech|ce|civil|bt|biotech|mba|mca|bca|bba|be|btech|mtech|phd|library|placement|placements|exam|timetable|syllabus|results|building|auditorium|kle|kletech|bvb|campus|hubballi|scholarship|cutoff|eligibility|contact|phone|email|address)\b",
    re.IGNORECASE,
)

# Direct pattern debug
word = "depatments"
print(f"Testing: '{word}'")
print(f"Match object: {CAMPUS_DOMAIN_PATTERN.search(word)}")
print(f"Bool: {bool(CAMPUS_DOMAIN_PATTERN.search(word))}")

# Also test the exact word from log
word2 = "depatments"
print()
print(f"Chars: {list(word2)}")
# depatments = d-e-p-a-t-m-e-n-t-s
# depatments? -> matches depatments or depatment
print(f"Pattern literal 'depatments?' search: {re.search(r'depatments?', word2)}")
