"""Standalone Query Rewriter with Acronym Expansion and Synonym Enhancement for multi-turn RAG retrieval."""

import re
from typing import Any


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
            (r"\b(all engineering departments?|what departments exist|list of departments|schools and departments)\b", "School of Computer Science Engineering Civil Mechanical Electrical Electronics Biotechnology Architecture Design Management departments"),
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

        # Step 2: Multi-turn Pronoun Resolution & Topic Tracking
        if history:
            has_pronoun = bool(self.PRONOUN_PATTERN.search(query_text))

            # Detect explicit topic in current query
            explicit_topic = self._detect_explicit_topic(query_text)

            if has_pronoun:
                user_messages: list[str] = []
                if isinstance(history, str):
                    for line in reversed(history.split("\n")):
                        if line.lower().startswith("user:"):
                            user_messages.append(line.split(":", 1)[1].strip())
                elif isinstance(history, (list, tuple)):
                    for msg in reversed(history):
                        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
                        if role == "user":
                            content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else str(msg))
                            user_messages.append(content)

                # Scan user messages from newest to oldest for a valid canonical subject
                canonical_subject = None
                for msg in user_messages:
                    subject = self._extract_subject(msg)
                    if subject:
                        canonical_subject = subject
                        break

                if canonical_subject and not explicit_topic:
                    query_text = self.PRONOUN_PATTERN.sub(canonical_subject, query_text)

        # Step 3: Domain-specific synonym enrichment and campus context resolution
        q_lower = query_text.lower()
        has_branch_term = any(b in q_lower for b in ("belagavi", "belgaum", "sheshgiri", "bengaluru", "bangalore"))
        campus_context = "Dr M S Sheshgiri Campus Belagavi" if has_branch_term else "KLE Technological University BVB Campus Vidyanagar Hubballi"

        if any(k in q_lower for k in ("department list", "list of departments", "all departments", "which departments", "course list", "program list", "schools list")):
            query_text = f"{query_text} Schools Departments List Civil Mechanical Electrical Electronics Computer Science Information Science Biotechnology Architecture Programs Courses {campus_context}"
        elif any(k in q_lower for k in ("course", "courses", "program", "programs", "degree", "curriculum")):
            query_text = f"{query_text} Undergraduate Postgraduate B.E. M.Tech MBA MCA BCA BBA Programs Courses Offered Curriculum Degree {campus_context}"

        elif "hostel" in q_lower:
            query_text = f"{query_text} hostel facilities canteens food boys girls mess dining residential rooms security recreation internet Wi-Fi {campus_context}"
        elif "library" in q_lower or "borrow" in q_lower or "book" in q_lower:
            query_text = f"{query_text} Central Library Block C 2nd floor second floor Books volumes titles ebooks journals Continio borrow timings reference section location {campus_context}"
        elif "placement" in q_lower or "placements" in q_lower or "hire" in q_lower:
            query_text = f"{query_text} Placement cell placement brochure recruiters companies training statistics package average package {campus_context}"
        elif any(k in q_lower for k in ("timetable", "time table", "circular", "exam", "assessment")):
            query_text = f"{query_text} timetable circular exam theory examinations April 2025 Semester Assessment schedule notices notice board ref 5221 commencement {campus_context}"
        elif any(k in q_lower for k in ("canteen", "mess", "dining", "food", "cafeteria")):
            query_text = f"{query_text} canteen dining food mess canteens cafeterias hostel canteens {campus_context}"
        elif any(k in q_lower for k in ("sports", "gym", "ground", "fitness", "facilities", "recreation")):
            query_text = f"{query_text} sports gym ground gymnasium indoor games facilities banking ATM medical health center {campus_context}"
        elif any(k in q_lower for k in ("admission", "admissions", "apply", "admit")):
            query_text = f"{query_text} Admissions Office Admission Cell Administrative Officer Registrar Coordinator application eligibility counseling {campus_context}"
        elif any(k in q_lower for k in ("location", "where is", "address", "where")):
            query_text = f"{query_text} campus location address building block floor office {campus_context}"

        return query_text

    def _detect_explicit_topic(self, text: str) -> str | None:
        """Detect if the query contains an explicit new domain entity."""
        lower = text.lower()
        topic_terms = [
            "library", "canteen", "mess", "hostel", "placement", "placements",
            "admission", "admissions", "fee", "fees", "scholarship", "exam",
            "timetable", "department", "computer science", "mechanical",
            "civil", "biotech", "sports", "gym"
        ]
        for term in topic_terms:
            if term in lower:
                return term
        return None

    def _extract_subject(self, text: str) -> str | None:
        """Extract primary subject noun phrase from previous user question.
        Returns None if text contains pronouns or generic non-entity terms.
        """
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
            "how do i get to the",
            "how do i find the",
        ]
        sub_candidate = clean
        for prefix in prefixes:
            if lower_clean.startswith(prefix):
                sub_candidate = clean[len(prefix) :].strip()
                break

        if not sub_candidate:
            return None

        # Clean trailing location suffixes
        for suffix in [" located in campus", " located", " situated", " on campus"]:
            if sub_candidate.lower().endswith(suffix):
                sub_candidate = sub_candidate[: -len(suffix)].strip()

        # Reject candidates that contain pronouns or generic non-subject terms
        if self.PRONOUN_PATTERN.search(sub_candidate):
            return None

        generic_terms = {
            "timings", "timing", "hours", "open", "closed", "fee", "cost",
            "schedule", "time", "date", "status", "info", "details"
        }
        words = sub_candidate.lower().split()
        if all(w in generic_terms for w in words):
            return None

        return sub_candidate.title()
