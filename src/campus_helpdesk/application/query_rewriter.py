"""Standalone Query Rewriter with Acronym Expansion and Synonym Enhancement for multi-turn RAG retrieval."""

import re
from typing import Any
from collections.abc import Sequence

from campus_helpdesk.domain.conversation import ChatMessage


class QueryRewriter:
    """Rewrites follow-up questions into standalone queries and expands campus acronyms/synonyms."""

    PRONOUN_PATTERN = re.compile(
        r"\b(it|its|they|their|them|that|this|the place|the department|there|here)\b",
        re.IGNORECASE,
    )

    def rewrite(self, query: str, history: Any = None) -> str:
        """Rewrite query with acronym expansion, synonym enrichment, and context resolution."""
        query_text = query.strip()
        if not query_text:
            return ""

        # Step 1: Acronym and Synonym Expansion
        expanded_text = query_text

        # 1.1 Multi-word & Specific Acronyms
        acronym_map = [
            (r"\b(BE|B\.E\.|B\.E)\b", "Bachelor of Engineering B.E. BE"),
            (r"\b(BTech|B\.Tech)\b", "Bachelor of Technology B.Tech"),
            (r"\b(MTech|M\.Tech)\b", "Master of Technology M.Tech"),
            (r"\b(PhD|Ph\.D)\b", "Doctor of Philosophy Ph.D"),
            (r"\b(BBA|B\.B\.A)\b", "Bachelor of Business Administration BBA"),
            (r"\b(BCA|B\.C\.A)\b", "Bachelor of Computer Applications BCA"),
            (r"\b(MCA|M\.C\.A)\b", "Master of Computer Applications MCA"),
            (r"\b(MBA|M\.B\.A)\b", "Master of Business Administration MBA"),
            (r"\b(Dept|Depts|dept|depts)\b", "Department"),
            (r"\b(VC|V\.C\.)\b", "Vice Chancellor"),
            (r"\b(HOD|H\.O\.D\.)\b", "Head of Department"),
            (r"\b(ISE|I\.S\.E\.)\b", "Information Science & Engineering ISE Information Science and Engineering"),
            (r"\b(CSE|C\.S\.E\.)\b", "Computer Science & Engineering CSE Computer Science and Engineering"),
            (r"\b(ECE|E\.C\.E\.)\b", "Electronics & Communication Engineering ECE Electronics and Communication Engineering"),
            (r"\b(EEE|E\.E\.E\.)\b", "Electrical & Electronics Engineering EEE Electrical and Electronics Engineering"),
            (r"\bME\b", "Mechanical Engineering"),  # Uppercase ME only
            (r"\b(Mech|mech)\b", "Mechanical Engineering"),
            (r"\b(CE|C\.E\.)\b", "Civil Engineering"),
            (r"\b(BT|B\.T\.)\b", "Biotechnology"),
            (r"\b(Biotech|biotech)\b", "Biotechnology"),
        ]

        for pattern, replacement in acronym_map:
            flags = 0 if "ME" in pattern else re.IGNORECASE
            if re.search(pattern, expanded_text, flags):
                expanded_text = re.sub(pattern, replacement, expanded_text, flags=flags)

        # Step 1.5: Spelling corrections
        spelling_map = [
            (r"\blibery\b", "library"),
            (r"\bcolage\b", "college"),
            (r"\bvce\b", "vice"),
            (r"\bchancelor\b", "chancellor"),
            (r"\bqota\b", "quota"),
            (r"\bfe\b", "fee"),
            (r"\bmes\b", "mess"),
            (r"\btabel\b", "table"),
            (r"\bwhre\b", "where"),
            (r"\bdeprtments\b", "departments"),
        ]
        for pattern, replacement in spelling_map:
            expanded_text = re.sub(pattern, replacement, expanded_text, flags=re.IGNORECASE)

        query_text = expanded_text

        # Step 2: Multi-turn Pronoun Resolution
        if history:
            has_pronoun = bool(self.PRONOUN_PATTERN.search(query_text))
            if has_pronoun:
                last_user_msg = None
                if isinstance(history, str):
                    for line in reversed(history.split("\n")):
                        if line.lower().startswith("user:"):
                            last_user_msg = line.split(":", 1)[1].strip()
                            break
                elif isinstance(history, (list, tuple)):
                    for msg in reversed(history):
                        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
                        if role == "user":
                            last_user_msg = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else str(msg))
                            break

                if last_user_msg:
                    subject = self._extract_subject(last_user_msg)
                    if subject:
                        query_text = self.PRONOUN_PATTERN.sub(subject, query_text)

        # Step 3: Domain-specific synonym enrichment for short general queries
        q_lower = query_text.lower()
        if any(k in q_lower for k in ("branch", "department", "school of", "schools", "course list", "program list")):
            query_text = f"{query_text} Schools Departments List Civil Mechanical Electrical Electronics Computer Science Information Science Biotechnology Architecture Programs Courses"
        elif any(k in q_lower for k in ("courses offered", "what courses", "programs offered", "list of courses")):
            query_text = f"{query_text} Undergraduate Postgraduate B.E. M.Tech MBA MCA BCA BBA Programs Courses Offered"

        elif "hostel" in q_lower:
            query_text = f"{query_text} hostel facilities canteens food boys girls mess dining residential rooms security recreation internet Wi-Fi"
        elif "library" in q_lower or "borrow" in q_lower or "book" in q_lower:
            query_text = f"{query_text} Central Library Block C 2nd floor second floor Books volumes titles ebooks journals Continio borrow timings reference section location"
        elif "placement" in q_lower or "placements" in q_lower or "hire" in q_lower:
            query_text = f"{query_text} Placement cell placement brochure recruiters companies training statistics package average package"
        elif any(k in q_lower for k in ("timetable", "time table", "circular", "exam", "assessment")):
            query_text = f"{query_text} timetable circular exam theory examinations April 2025 Semester Assessment schedule notices notice board ref 5221 commencement"
        elif any(k in q_lower for k in ("canteen", "mess", "dining", "food", "cafeteria")):
            query_text = f"{query_text} canteen dining food mess canteens cafeterias hostel canteens"
        elif any(k in q_lower for k in ("sports", "gym", "ground", "fitness", "facilities", "recreation")):
            query_text = f"{query_text} sports gym ground gymnasium indoor games facilities banking ATM medical health center"
        elif any(k in q_lower for k in ("office", "location", "where is", "room")):
            query_text = f"{query_text} office room block location School CSE HOD CARR registrar placement cell admin block Room 401"

        return query_text

    def _extract_subject(self, text: str) -> str | None:
        """Extract primary subject noun phrase from previous user question."""
        clean = text.strip().rstrip("?").rstrip(".")
        lower_clean = clean.lower()

        prefixes = [
            "where is the",
            "where is",
            "what is the",
            "what is",
            "when is the",
            "when is",
            "tell me about the",
            "tell me about",
            "how to apply for",
            "how to get into",
        ]
        for prefix in prefixes:
            if lower_clean.startswith(prefix):
                sub = clean[len(prefix) :].strip()
                if sub:
                    for suffix in [" located in campus", " located", " situated", " on campus"]:
                        if sub.lower().endswith(suffix):
                            sub = sub[: -len(suffix)].strip()
                    return sub.title()

        return clean.title()
