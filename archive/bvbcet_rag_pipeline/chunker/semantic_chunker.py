"""Production-grade Semantic Markdown Chunking Engine.

Recursively scans Markdown documents, preserves heading hierarchy and atomic block structures
(tables, lists, code blocks, block quotes, horizontal rules), and produces structured Chunk objects.
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """Dataclass representing a semantic Markdown chunk."""

    id: str
    title: str
    heading: str
    level: int
    text: str
    token_count: int


@dataclass
class SectionBlock:
    """Represents an atomic block of text within a section (table, codeblock, list, quote, paragraph)."""

    block_type: str  # 'code', 'table', 'list', 'quote', 'hr', 'paragraph'
    text: str


@dataclass
class SemanticSection:
    """Represents a section bounded by a Markdown heading."""

    title: str
    heading: str
    level: int
    blocks: List[SectionBlock]

    @property
    def full_text(self) -> str:
        """Combine block texts preserving paragraph separation."""
        return "\n\n".join(b.text.strip() for b in self.blocks if b.text.strip())


class SemanticMarkdownChunker:
    """Semantic Markdown Chunking Engine."""

    def __init__(
        self,
        ideal_tokens: int = 750,
        max_tokens: int = 1000,
        overlap_tokens: int = 150,
    ) -> None:
        self.ideal_tokens = ideal_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

        # Approx 4 characters per token heuristic for character-based splitter
        char_chunk_size = max_tokens * 4
        char_chunk_overlap = overlap_tokens * 4

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=char_chunk_size,
            chunk_overlap=char_chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count using word/punctuation tokenization heuristic."""
        if not text:
            return 0
        words = len(text.split())
        return int(words * 1.3)

    def parse_blocks(self, raw_lines: List[str]) -> List[SectionBlock]:
        """Parse lines into atomic SectionBlocks (tables, lists, codeblocks, quotes, hr)."""
        blocks: List[SectionBlock] = []
        current_lines: List[str] = []
        current_type: Optional[str] = None

        in_code_block = False
        code_lines: List[str] = []

        def flush_current():
            nonlocal current_lines, current_type
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    blocks.append(SectionBlock(block_type=current_type or "paragraph", text=text))
                current_lines = []
                current_type = None

        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]

            # Code Block handling
            if line.strip().startswith("```"):
                if not in_code_block:
                    flush_current()
                    in_code_block = True
                    code_lines = [line]
                else:
                    code_lines.append(line)
                    in_code_block = False
                    blocks.append(SectionBlock(block_type="code", text="\n".join(code_lines)))
                    code_lines = []
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Horizontal Rule
            if re.match(r"^[-*_]{3,}$", line.strip()):
                flush_current()
                blocks.append(SectionBlock(block_type="hr", text=line.strip()))
                i += 1
                continue

            # Table Row
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if current_type != "table":
                    flush_current()
                    current_type = "table"
                current_lines.append(line)
                i += 1
                continue

            # Block Quote
            if line.strip().startswith(">"):
                if current_type != "quote":
                    flush_current()
                    current_type = "quote"
                current_lines.append(line)
                i += 1
                continue

            # List Item
            if re.match(r"^(\s*[-*+]|\s*\d+\.)\s+", line):
                if current_type != "list":
                    flush_current()
                    current_type = "list"
                current_lines.append(line)
                i += 1
                continue

            # Blank line breaks paragraph/list/table/quote
            if not line.strip():
                flush_current()
                i += 1
                continue

            # Regular Paragraph text
            if current_type not in (None, "paragraph"):
                flush_current()
            current_type = "paragraph"
            current_lines.append(line)
            i += 1

        flush_current()
        return blocks

    def parse_semantic_sections(self, file_path: Path, text: str) -> List[SemanticSection]:
        """Parse document into SemanticSections bounded by heading levels (# to #####)."""
        lines = text.splitlines()
        doc_title = file_path.stem.replace("_", " ").title()

        sections: List[SemanticSection] = []
        current_heading = doc_title
        current_level = 1
        section_lines: List[str] = []

        for line in lines:
            heading_match = re.match(r"^(#{1,5})\s+(.+)$", line.strip())
            if heading_match:
                # Flush previous section
                if section_lines:
                    blocks = self.parse_blocks(section_lines)
                    if blocks:
                        sections.append(
                            SemanticSection(
                                title=doc_title,
                                heading=current_heading,
                                level=current_level,
                                blocks=blocks,
                            )
                        )
                    section_lines = []

                level_str, heading_text = heading_match.groups()
                current_level = len(level_str)
                current_heading = heading_text.strip()
                if current_level == 1:
                    doc_title = current_heading
            else:
                section_lines.append(line)

        if section_lines:
            blocks = self.parse_blocks(section_lines)
            if blocks:
                sections.append(
                    SemanticSection(
                        title=doc_title,
                        heading=current_heading,
                        level=current_level,
                        blocks=blocks,
                    )
                )

        return sections

    def chunk_section(self, section: SemanticSection, file_slug: str, section_idx: int) -> List[Chunk]:
        """Split a single SemanticSection into Chunks without mixing headings."""
        full_section_text = section.full_text
        if not full_section_text.strip():
            return []

        section_tokens = self.count_tokens(full_section_text)

        # Context prefix to preserve heading context in chunk text
        heading_prefix = f"# {section.title}\n## {section.heading}\n\n" if section.heading != section.title else f"# {section.title}\n\n"

        # If section fits within maximum token limit, return as single chunk
        if section_tokens <= self.max_tokens:
            chunk_text = f"{heading_prefix}{full_section_text}".strip()
            return [
                Chunk(
                    id=f"{file_slug}_{section_idx}_0",
                    title=section.title,
                    heading=section.heading,
                    level=section.level,
                    text=chunk_text,
                    token_count=self.count_tokens(chunk_text),
                )
            ]

        # Over-sized section: use RecursiveCharacterTextSplitter on full section text
        sub_texts = self.text_splitter.split_text(full_section_text)
        chunks: List[Chunk] = []

        for sub_idx, sub_text in enumerate(sub_texts):
            chunk_content = f"{heading_prefix}{sub_text}".strip()
            chunks.append(
                Chunk(
                    id=f"{file_slug}_{section_idx}_{sub_idx}",
                    title=section.title,
                    heading=section.heading,
                    level=section.level,
                    text=chunk_content,
                    token_count=self.count_tokens(chunk_content),
                )
            )

        return chunks

    def process_text(self, content: str, file_path: Path) -> List[Chunk]:
        """Parse raw Markdown string into a list of Chunk objects."""
        if not content.strip():
            return []

        file_slug = file_path.stem.lower()
        sections = self.parse_semantic_sections(file_path, content)

        file_chunks: List[Chunk] = []
        for sec_idx, section in enumerate(sections):
            section_chunks = self.chunk_section(section, file_slug, sec_idx)
            file_chunks.extend(section_chunks)

        return file_chunks

    def process_file(self, file_path: Path) -> List[Chunk]:
        """Parse a single Markdown file into a list of Chunk objects."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.process_text(content, file_path)
        except Exception:
            return []

    def scan_directory(self, markdown_dir: Path) -> List[Chunk]:
        """Recursively scan directory for .md files and return list of Chunk objects."""
        all_chunks: List[Chunk] = []
        if not markdown_dir.exists() or not markdown_dir.is_dir():
            return all_chunks

        # rglob for unlimited nested subfolder support
        md_files = sorted(list(markdown_dir.rglob("*.md")))
        for md_file in md_files:
            chunks = self.process_file(md_file)
            all_chunks.extend(chunks)

        return all_chunks
