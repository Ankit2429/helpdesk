"""Conversational Question Generator Module for RAG Evaluation.

Synthesizes short, natural, visitor-centric helpdesk questions simulating 8 real-world personas
(newly admitted student, parent, visitor, prospective student, guest, lost student, etc.).
Strictly avoids document-centric, bureaucratic, or metadata-referencing phrasing.
"""

import logging
import math
import random
import re
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from evaluation.dataset_generator.config import GeneratorConfig
from evaluation.dataset_generator.reader import MarkdownDocument, SectionBlock

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQuestionCandidate:
    """Candidate QA pair synthesized from a Markdown section."""

    question: str
    expected_answer: str
    section_heading: str
    perspective: str
    difficulty: str
    keywords: List[str]


def _clean_entity_name(raw_text: str) -> str:
    """Cleans section heading or title into a clean human entity name."""
    text = re.sub(r"^(pdf document:|page \d+|notification|table showing|schedule of|list of|important notice|circular)", "", raw_text, flags=re.IGNORECASE)
    text = re.sub(r"_[a-f0-9]{6,}$", "", text)  # Strip hash suffixes
    text = re.sub(r"[^\w\s\-\&]", " ", text)
    text = " ".join(text.split()).strip()
    return text if len(text) > 2 else "the department"


class QuestionGenerator:
    """Generates realistic conversational helpdesk questions from Markdown document sections."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.personas = config.personas

    def calculate_question_count(self, doc: MarkdownDocument) -> int:
        """Determines target question count (between min 5 and max 20) based on document size."""
        words = doc.total_word_count
        sections_count = len(doc.sections)
        calculated = math.ceil(words / self.config.words_per_question)
        calculated = max(calculated, sections_count * 2)
        return max(self.config.min_questions_per_doc, min(self.config.max_questions_per_doc, calculated))

    def _extract_keywords(self, text: str) -> List[str]:
        """Extracts clean keywords from text snippet."""
        clean_text = re.sub(r"[^\w\s]", "", text)
        words = [w.lower() for w in clean_text.split() if len(w) > 3]
        stopwords = {"this", "that", "with", "from", "have", "more", "also", "were", "been", "which", "their", "about", "pdf", "page", "source"}
        filtered = [w for w in words if w not in stopwords]
        return list(dict.fromkeys(filtered))[:6]

    def _generate_natural_queries(
        self,
        category: str,
        entity: str,
        section_text: str,
        heading: str,
    ) -> List[Tuple[str, str, str]]:
        """Generates natural, short conversational questions tailored to category & real-world personas.

        Returns list of (question_text, persona, difficulty) tuples.
        """
        queries: List[Tuple[str, str, str]] = []
        e_clean = _clean_entity_name(entity)
        h_clean = _clean_entity_name(heading)

        # 1. ADMISSION CATEGORY
        if category == "Admission":
            queries.extend([
                ("How do I get admission here?", "prospective student", "easy"),
                ("Where is the admission office?", "first-time campus visitor", "easy"),
                ("Which documents should I bring for admission?", "newly admitted student", "medium"),
                ("Can I get admission through KCET?", "prospective student", "medium"),
                ("What is the admission process?", "parent accompanying student", "medium"),
                ("Who should I contact for admission information?", "prospective student", "easy"),
            ])
            if "international" in h_clean.lower() or "nri" in h_clean.lower():
                queries.append(("How can international or NRI students apply for admission?", "prospective student", "hard"))
            elif "eligibility" in h_clean.lower():
                queries.append((f"What is the eligibility criteria for {e_clean}?", "prospective student", "medium"))
            elif "lateral" in h_clean.lower() or "diploma" in h_clean.lower():
                queries.append(("Can diploma students join directly through lateral entry?", "prospective student", "hard"))

        # 2. NAVIGATION CATEGORY
        elif category == "Navigation":
            target = h_clean if len(h_clean) > 3 else e_clean
            queries.extend([
                (f"Where is {target}?", "student lost on campus", "easy"),
                (f"How do I reach the {target}?", "first-time campus visitor", "easy"),
                (f"Can you guide me to the {target}?", "guest attending an event", "easy"),
                ("Is there parking for visitors on campus?", "parent accompanying student", "medium"),
                ("Where is the canteen?", "student lost on campus", "easy"),
                ("Where is the nearest washroom?", "guest attending an event", "easy"),
                ("Where is the principal's office?", "student looking for administrative offices", "medium"),
                ("How do I reach the examination section?", "student looking for administrative offices", "medium"),
            ])

        # 3. DEPARTMENTS CATEGORY
        elif category == "Departments":
            dept_name = h_clean if len(h_clean) > 3 else e_clean
            queries.extend([
                (f"What courses are offered in {dept_name}?", "prospective student", "easy"),
                (f"Where is the {dept_name} department?", "student lost on campus", "easy"),
                (f"Which block is {dept_name} in?", "student visiting another department", "medium"),
                (f"Can I meet a faculty member from {dept_name}?", "parent accompanying student", "medium"),
                (f"Does this college have a department for {dept_name}?", "prospective student", "easy"),
            ])

        # 4. HOSTEL CATEGORY
        elif category == "Hostel":
            queries.extend([
                ("Is hostel facility available?", "parent accompanying student", "easy"),
                ("How do I apply for hostel accommodation?", "newly admitted student", "medium"),
                ("Are hostel rooms shared?", "parent accompanying student", "medium"),
                ("Is Wi-Fi available in the hostel?", "newly admitted student", "easy"),
                ("How much are the hostel fees?", "parent accompanying student", "easy"),
                ("Where is the boys hostel?", "first-time campus visitor", "easy"),
                ("Where is the girls hostel?", "first-time campus visitor", "easy"),
            ])

        # 5. FACILITIES CATEGORY
        elif category == "Facilities":
            fac = h_clean if len(h_clean) > 3 else "the facility"
            queries.extend([
                (f"Where is the {fac}?", "first-time campus visitor", "easy"),
                ("Is there a gym inside the campus?", "newly admitted student", "easy"),
                ("Does the college have a medical room or clinic?", "parent accompanying student", "medium"),
                ("Is Wi-Fi available on campus for students?", "newly admitted student", "easy"),
                ("Where is the library located?", "student lost on campus", "easy"),
                ("Is there an ATM inside the campus?", "guest attending an event", "easy"),
                ("Is there a cafeteria or canteen on campus?", "first-time campus visitor", "easy"),
            ])

        # 6. FEES CATEGORY
        elif category == "Fees":
            queries.extend([
                ("How much is the tuition fee?", "parent accompanying student", "easy"),
                ("Can I pay fees online?", "newly admitted student", "easy"),
                ("Are scholarships available for students?", "prospective student", "medium"),
                ("When is the last date to pay fees?", "newly admitted student", "medium"),
                ("Where do I pay the college fees?", "parent accompanying student", "easy"),
            ])

        # 7. PLACEMENT CATEGORY
        elif category == "Placement":
            queries.extend([
                ("Do companies visit this college for placement?", "parent accompanying student", "easy"),
                ("Which companies recruit students from here?", "prospective student", "medium"),
                ("What is the placement percentage?", "prospective student", "easy"),
                ("Are internships available for students?", "newly admitted student", "medium"),
                ("What is the highest package offered in campus placement?", "prospective student", "medium"),
            ])

        # 8. FACULTY CATEGORY
        elif category == "Faculty":
            f_name = h_clean if len(h_clean) > 3 else "the department"
            queries.extend([
                (f"How can I meet the HOD of {f_name}?", "student visiting another department", "medium"),
                ("Where is the faculty room?", "student lost on campus", "easy"),
                ("Can I talk to a professor?", "parent accompanying student", "easy"),
                ("Where is the staff room located?", "first-time campus visitor", "easy"),
            ])

        # 9. GENERAL / MISC CATEGORY
        else:
            queries.extend([
                ("What are the college timings?", "first-time campus visitor", "easy"),
                ("Where should visitors enter the campus?", "first-time campus visitor", "easy"),
                ("Can outsiders visit the campus?", "guest attending an event", "easy"),
                ("Where do I collect my student ID card?", "newly admitted student", "medium"),
                ("Where is the examination office?", "student looking for administrative offices", "medium"),
                ("Where can I submit my documents?", "newly admitted student", "easy"),
            ])

        return queries

    def generate_questions(self, doc: MarkdownDocument) -> List[GeneratedQuestionCandidate]:
        """Generates candidate conversational questions for a Markdown document.

        Args:
            doc: MarkdownDocument instance.

        Returns:
            List of GeneratedQuestionCandidate instances.
        """
        target_count = self.calculate_question_count(doc)
        all_candidates: List[GeneratedQuestionCandidate] = []

        # Determine category from metadata or filename
        category = doc.metadata.get("assigned_category", "Misc")

        for section in doc.sections:
            content = section.content.strip()
            heading = section.heading.strip()

            if len(content) < 25:
                continue

            # Ignore PDF noise sections
            if heading.lower().startswith("pdf document:") or heading.lower().startswith("source:"):
                continue

            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if len(s.strip()) > 15]
            expected_ans = sentences[0] if sentences else content[:150]

            keywords = self._extract_keywords(content)

            # Generate natural conversational helpdesk queries
            raw_queries = self._generate_natural_queries(
                category=category,
                entity=doc.title,
                section_text=content,
                heading=heading,
            )

            for q_text, persona, diff in raw_queries:
                # Guarantee NO document-centric metadata phrases
                if "as stated in" in q_text or "pdf document" in q_text.lower() or "information?" in q_text:
                    continue

                all_candidates.append(
                    GeneratedQuestionCandidate(
                        question=q_text,
                        expected_answer=expected_ans,
                        section_heading=_clean_entity_name(heading),
                        perspective=persona,
                        difficulty=diff,
                        keywords=keywords,
                    )
                )

        if not all_candidates:
            return []

        # Deduplicate identical question strings
        unique_map = {}
        for c in all_candidates:
            if c.question not in unique_map:
                unique_map[c.question] = c
        unique_candidates = list(unique_map.values())

        # Sample up to target_count deterministically
        if len(unique_candidates) > target_count:
            random.seed(42)
            selected = random.sample(unique_candidates, target_count)
        else:
            selected = unique_candidates

        return selected
