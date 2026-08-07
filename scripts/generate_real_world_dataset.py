import uuid
import yaml
import os

# Seed data for each category. Each entry is a list of possible user turns.
SEED_DATA = {
    "admissions": [
        {
            "simple": "What are the admission requirements?",
            "follow_up": "Do I need a good GPA?",
            "ambiguous": "Is it hard to get in?",
            "typo": "What are the admittion requirments?",
            "incomplete": "Admission requirements",
        }
    ],
    "fees": [
        {
            "simple": "What is the tuition fee for B.Tech?",
            "follow_up": "Are there any scholarships?",
            "ambiguous": "How much does it cost?",
            "typo": "What is the tuition fee for B.Tech?",
            "incomplete": "Tuition fee B.Tech",
        }
    ],
    "departments": [
        {
            "simple": "List the engineering departments.",
            "follow_up": "What courses does the Computer Science department offer?",
            "ambiguous": "Which department is best?",
            "typo": "List the enginnering departments.",
            "incomplete": "Engineering departments",
        }
    ],
    "faculty": [
        {
            "simple": "Who is the head of the Mechanical department?",
            "follow_up": "What is his research area?",
            "ambiguous": "Tell me about the faculty.",
            "typo": "Who is the head of the Mechnical department?",
            "incomplete": "Head of Mechanical department",
        }
    ],
    "hostel": [
        {
            "simple": "How many hostel rooms are there?",
            "follow_up": "What is the cost per semester?",
            "ambiguous": "Is the hostel good?",
            "typo": "How many hostle rooms are there?",
            "incomplete": "Hostel rooms count",
        }
    ],
    "library": [
        {
            "simple": "What are the library timings?",
            "follow_up": "Can I borrow books for a month?",
            "ambiguous": "Is the library open?",
            "typo": "What are the libraray timings?",
            "incomplete": "Library timings",
        }
    ],
    "navigation": [
        {
            "simple": "How do I get to the sports complex from the main gate?",
            "follow_up": "Is there a shortcut?",
            "ambiguous": "Where is it?",
            "typo": "How do I get to the sport complex from the main gate?",
            "incomplete": "Directions to sports complex",
        }
    ],
    "placements": [
        {
            "simple": "What is the placement rate for 2023?",
            "follow_up": "Which companies visited?",
            "ambiguous": "Are placements good?",
            "typo": "What is the placement rate for 2023?",
            "incomplete": "Placement rate 2023",
        }
    ],
    "scholarships": [
        {
            "simple": "What scholarships are available for merit students?",
            "follow_up": "How to apply for them?",
            "ambiguous": "Are there any scholarships?",
            "typo": "What scholarships are avalable for merit students?",
            "incomplete": "Scholarships for merit",
        }
    ],
    "sports": [
        {
            "simple": "What sports facilities are on campus?",
            "follow_up": "Can I join the basketball team?",
            "ambiguous": "Do you have sports?",
            "typo": "What sports facilities are on campus?",
            "incomplete": "Sports facilities",
        }
    ],
    "clubs": [
        {
            "simple": "List the student clubs.",
            "follow_up": "How to join the robotics club?",
            "ambiguous": "Which clubs exist?",
            "typo": "List the student clbs.",
            "incomplete": "Student clubs",
        }
    ],
    "events": [
        {
            "simple": "When is the cultural fest this year?",
            "follow_up": "What are the main events?",
            "ambiguous": "Any events coming up?",
            "typo": "When is the cultural fest this year?",
            "incomplete": "Cultural fest date",
        }
    ],
    "office_timings": [
        {
            "simple": "What are the admin office timings?",
            "follow_up": "Are they open on weekends?",
            "ambiguous": "When is office open?",
            "typo": "What are the admin office timings?",
            "incomplete": "Admin office timings",
        }
    ],
    "contact_information": [
        {
            "simple": "Provide the contact number for the admissions office.",
            "follow_up": "What is the email address?",
            "ambiguous": "How can I contact the college?",
            "typo": "Provide the contact number for the admissions ofice.",
            "incomplete": "Admissions office contact",
        }
    ],
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "evaluation", "datasets", "real_world.yaml")

def build_conversation(seed_entry):
    """Create a multi‑turn conversation list from a seed entry dictionary."""
    turns = []
    # Simple question
    turns.append(seed_entry["simple"])
    # Follow‑up
    turns.append(seed_entry["follow_up"])
    # Ambiguous
    turns.append(seed_entry["ambiguous"])
    # Typo
    turns.append(seed_entry["typo"])
    # Incomplete
    turns.append(seed_entry["incomplete"])
    return turns

def generate_dataset():
    dataset = {}
    for category, entries in SEED_DATA.items():
        convs = []
        for entry in entries:
            conv_id = str(uuid.uuid4())
            convs.append({
                "id": conv_id,
                "turns": build_conversation(entry),
                "expected_answer": "",
                "expected_citations": []
            })
        dataset[category] = convs
    # Write YAML
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(dataset, f, sort_keys=False)
    print(f"Real‑world evaluation dataset written to {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_dataset()
