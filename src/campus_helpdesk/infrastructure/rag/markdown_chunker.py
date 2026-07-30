"""Hierarchical Markdown and Section-Aware Semantic Chunker."""

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from campus_helpdesk.domain.knowledge import KnowledgeDocument


def _infer_department(filename: str, category: str, content: str) -> str:
    """Infers department or academic domain from document metadata and content."""
    fn_lower = filename.lower()
    cat_lower = category.lower()
    content_sub = content[:500].lower()

    if "computer" in fn_lower or "cse" in fn_lower or "computer" in content_sub:
        return "Computer Science & Engineering"
    elif "electronics" in fn_lower or "ece" in fn_lower or "electronics" in content_sub:
        return "Electronics & Communication Engineering"
    elif "mechanical" in fn_lower or "mechanical" in content_sub:
        return "Mechanical Engineering"
    elif "civil" in fn_lower or "civil" in content_sub:
        return "Civil Engineering"
    elif "biotech" in fn_lower or "biotechnology" in content_sub:
        return "Biotechnology"
    elif "law" in fn_lower or "law" in cat_lower or "law" in content_sub:
        return "School of Law"
    elif "bba" in fn_lower or "mba" in fn_lower or "management" in content_sub:
        return "School of Management & Business Administration"
    elif "admission" in fn_lower or "admission" in cat_lower or "admission" in content_sub:
        return "Admissions & Registrar Cell"
    elif "fee" in fn_lower or "fee" in cat_lower:
        return "Accounts & Finance Office"
    elif "hostel" in fn_lower or "hostel" in cat_lower:
        return "Campus Hostel Administration"
    elif "placement" in fn_lower or "placement" in cat_lower:
        return "Career Development & Placement Cell"
    else:
        return "University Administration"


class MarkdownSemanticChunker:
    """Semantic section-aware Markdown chunker.

    Detects Markdown headers (#, ##, ###), tables, lists, and code blocks.
    Injects hierarchical breadcrumbs into chunk text and metadata.
    Never splits tables, bullet lists, numbered lists, or code blocks.
    """

    def __init__(
        self,
        min_chunk_chars: int = 250,
        max_chunk_chars: int = 2500,
        target_chunk_chars: int = 1500,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ) -> None:
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.target_chunk_chars = target_chunk_chars

    def _parse_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Parses Markdown text into typed structural blocks.

        Returns list of tuples: (block_type, block_text)
        block_types: 'header', 'table', 'list', 'code', 'paragraph'
        """
        lines = text.splitlines()
        blocks: List[Tuple[str, str]] = []
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]

            # 1. Header block
            if line.startswith("#"):
                blocks.append(("header", line))
                i += 1
                continue

            # 2. Fenced Code Block
            if line.strip().startswith("```"):
                code_lines = [line]
                i += 1
                while i < n:
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith("```"):
                        i += 1
                        break
                    i += 1
                blocks.append(("code", "\n".join(code_lines)))
                continue

            # 3. Table Block (lines starting/ending with | or containing |---|)
            if "|" in line and (line.strip().startswith("|") or line.strip().endswith("|")):
                table_lines = [line]
                i += 1
                while i < n and "|" in lines[i] and (lines[i].strip().startswith("|") or lines[i].strip().endswith("|")):
                    table_lines.append(lines[i])
                    i += 1
                blocks.append(("table", "\n".join(table_lines)))
                continue

            # 4. Bullet / Numbered List Block
            list_match = re.match(r"^\s*([*\-+]\s+|\d+\.\s+)", line)
            if list_match:
                list_lines = [line]
                i += 1
                while i < n:
                    next_line = lines[i]
                    if not next_line.strip():
                        # Empty line might end list if followed by non-indented text
                        if i + 1 < n and not re.match(r"^\s*([*\-+]\s+|\d+\.\s+|\s{2,})", lines[i + 1]):
                            break
                    elif re.match(r"^\s*([*\-+]\s+|\d+\.\s+|\s{2,})", next_line):
                        list_lines.append(next_line)
                    else:
                        break
                    i += 1
                blocks.append(("list", "\n".join(list_lines)))
                continue

            # 5. Paragraph / Text block
            if line.strip():
                para_lines = [line]
                i += 1
                while i < n:
                    next_line = lines[i]
                    if not next_line.strip() or next_line.startswith("#") or next_line.strip().startswith("```") or ("|" in next_line and next_line.strip().startswith("|")) or re.match(r"^\s*([*\-+]\s+|\d+\.\s+)", next_line):
                        break
                    para_lines.append(next_line)
                    i += 1
                blocks.append(("paragraph", "\n".join(para_lines)))
                continue

            i += 1

        return blocks

    def split_document(self, document: KnowledgeDocument) -> List[KnowledgeDocument]:
        """Splits Markdown document into section-aware chunks with hierarchical metadata."""
        content = document.content
        raw_metadata = dict(document.metadata)

        source_file = (
            raw_metadata.get("source_filename")
            or Path(raw_metadata.get("source", "unknown.md")).name
        )
        category = raw_metadata.get("category", "General")
        department = _infer_department(source_file, category, content)

        # Detect Page Title (H1 or first heading or title metadata)
        page_title = raw_metadata.get("title", "")
        if not page_title:
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if h1_match:
                page_title = h1_match.group(1).strip()
            else:
                page_title = Path(source_file).stem.replace("_", " ").title()

        blocks = self._parse_blocks(content)
        if not blocks:
            return [document]

        # Tracking state
        h1 = page_title
        h2 = ""
        h3 = ""
        current_heading_level = "H1"

        section_chunks: List[Dict[str, Any]] = []
        current_section_blocks: List[str] = []
        current_section_chars = 0

        for block_type, block_text in blocks:
            if block_type == "header":
                header_match = re.match(r"^(#+)\s+(.+)$", block_text)
                if header_match:
                    hashes, title = header_match.groups()
                    level = len(hashes)
                    title_clean = title.strip()

                    # Save previous section blocks if non-empty
                    if current_section_blocks:
                        section_chunks.append({
                            "content": "\n\n".join(current_section_blocks),
                            "h1": h1,
                            "h2": h2,
                            "h3": h3,
                            "heading_level": current_heading_level,
                        })
                        current_section_blocks = []
                        current_section_chars = 0

                    if level == 1:
                        h1 = title_clean
                        h2 = ""
                        h3 = ""
                        current_heading_level = "H1"
                    elif level == 2:
                        h2 = title_clean
                        h3 = ""
                        current_heading_level = "H2"
                    else:
                        h3 = title_clean
                        current_heading_level = f"H{level}"
                continue

            current_section_blocks.append(block_text)
            current_section_chars += len(block_text)

            # If section blocks exceed target size, flush section chunk
            if current_section_chars >= self.target_chunk_chars:
                section_chunks.append({
                    "content": "\n\n".join(current_section_blocks),
                    "h1": h1,
                    "h2": h2,
                    "h3": h3,
                    "heading_level": current_heading_level,
                })
                current_section_blocks = []
                current_section_chars = 0

        # Flush final section
        if current_section_blocks:
            section_chunks.append({
                "content": "\n\n".join(current_section_blocks),
                "h1": h1,
                "h2": h2,
                "h3": h3,
                "heading_level": current_heading_level,
            })

        # Merge tiny adjacent section chunks if < min_chunk_chars
        merged_chunks: List[Dict[str, Any]] = []
        for s_chunk in section_chunks:
            if merged_chunks and (len(merged_chunks[-1]["content"]) < self.min_chunk_chars or len(s_chunk["content"]) < self.min_chunk_chars):
                prev = merged_chunks[-1]
                prev["content"] += "\n\n" + s_chunk["content"]
                if s_chunk["h2"] and not prev["h2"]:
                    prev["h2"] = s_chunk["h2"]
                if s_chunk["h3"] and not prev["h3"]:
                    prev["h3"] = s_chunk["h3"]
            else:
                merged_chunks.append(s_chunk)

        # Build final KnowledgeDocument chunks with enriched breadcrumbs & metadata
        output_chunks: List[KnowledgeDocument] = []
        doc_type = "markdown" if source_file.endswith(".md") else "pdf_converted"

        for idx, sc in enumerate(merged_chunks, start=1):
            sec_h1 = sc["h1"] or page_title
            sec_h2 = sc["h2"]
            sec_h3 = sc["h3"]

            # Construct breadcrumb string: H1 > H2 > H3
            breadcrumb_parts = [p for p in [sec_h1, sec_h2, sec_h3] if p]
            breadcrumb = " > ".join(breadcrumb_parts)

            section_title = sec_h3 or sec_h2 or sec_h1

            chunk_meta = {
                **raw_metadata,
                "source_filename": source_file,
                "page_title": page_title,
                "section_title": section_title,
                "breadcrumb": breadcrumb,
                "department": department,
                "chunk_number": idx,
                "parent_document": source_file,
                "document_type": doc_type,
                "heading_level": sc["heading_level"],
            }

            # Prepend breadcrumb header directly to chunk content for maximum semantic & BM25 context
            header_prefix = f"[Location: {breadcrumb}]\n# {page_title}"
            if section_title and section_title != page_title:
                header_prefix += f" - {section_title}"
            
            full_content = f"{header_prefix}\n\n{sc['content'].strip()}"

            output_chunks.append(KnowledgeDocument(content=full_content, metadata=chunk_meta))

        return output_chunks
