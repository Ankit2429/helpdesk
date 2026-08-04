#!/usr/bin/env python
"""
audit_knowledge_base.py — Knowledge Base Completeness & Entity Inspector for AUNTII

Scans indexed RAG chunks (and source canonical files) to verify if specific campus entities
exist in the knowledge base, outputting a clear audit report for missing vs present information.
"""
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.stdout.reconfigure(encoding="utf-8")

from campus_helpdesk.config.settings import get_settings
from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline

AUDIT_ENTITIES = [
    ("Principal", [r"\bprincipal\b", r"\bhead of college\b"]),
    ("Vice Chancellor", [r"\bvice[\s\-]chancellor\b", r"\bvc\b", r"\bdr\.?\s*prakash\s*tewari\b", r"\bdr\.?\s*ashok\s*shettar\b"]),
    ("Registrar", [r"\bregistrar\b"]),
    ("Dean", [r"\bdean\b"]),
    ("HOD", [r"\bhod\b", r"\bhead of department\b"]),
    ("Hostel", [r"\bhostel\b", r"\bhostel timings\b", r"\baccommodat\b"]),
    ("Canteen", [r"\bcanteen\b", r"\bfood court\b", r"\bmess\b", r"\brefectory\b"]),
    ("Fees", [r"\bfee\b", r"\bfees\b", r"\btuition\b"]),
    ("Departments", [r"\bdepartment\b", r"\bise\b", r"\binformation science\b", r"\bcomputer science\b", r"\bcse\b", r"\bcivil\b", r"\bmechanical\b"]),
    ("Library", [r"\blibrary\b", r"\bbook bank\b", r"\blibrary hours\b"]),
    ("Block 7", [r"\bblock\s*7\b", r"\bbuilding 7\b"]),
    ("Sports Complex", [r"\bsports\b", r"\bgymkhana\b", r"\bplayground\b"]),
    ("Bus Facility", [r"\bbus\b", r"\btransport\b", r"\bcommute\b"]),
]

def main():
    print("=" * 80)
    print("AUNTII KNOWLEDGE BASE AUDIT & ENTITY INSPECTOR")
    print("=" * 80)

    settings = get_settings()
    pipeline = create_rag_pipeline(settings)
    if settings.faiss_index_path.exists():
        pipeline.load_index()

    similarity_store = pipeline._similarity_store
    docstore = None
    if hasattr(similarity_store, "_store") and similarity_store._store is not None:
        docstore = getattr(similarity_store._store, "docstore", None)
    
    docs = []
    if docstore and hasattr(docstore, "_dict"):
        docs = list(docstore._dict.values())
        print(f"Loaded {len(docs)} document chunks from FAISS docstore index.")
    else:
        # Fallback: scan canonical markdown files directly
        canonical_dir = Path("data/canonical_markdown")
        if canonical_dir.exists():
            for p in canonical_dir.rglob("*.md"):
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    docs.append({"page_content": text, "metadata": {"source": str(p)}})
                except Exception:
                    pass
            print(f"Loaded {len(docs)} files from data/canonical_markdown.")

    results: Dict[str, List[Dict[str, Any]]] = {}

    for entity_name, patterns in AUDIT_ENTITIES:
        regexes = [re.compile(p, re.IGNORECASE) for p in patterns]
        matches = []
        for doc in docs:
            content = getattr(doc, "page_content", "") or (doc.get("page_content") if isinstance(doc, dict) else "")
            metadata = getattr(doc, "metadata", {}) if not isinstance(doc, dict) else doc.get("metadata", {})
            source = metadata.get("source") or metadata.get("source_filename", "unknown")
            title = metadata.get("title") or metadata.get("Header 1", "Untitled")

            for reg in regexes:
                found = list(reg.finditer(content))
                if found:
                    for m in found[:2]:
                        start = max(0, m.start() - 50)
                        end = min(len(content), m.end() + 80)
                        snippet = content[start:end].replace("\n", " ").strip()
                        matches.append({
                            "source": source,
                            "title": title,
                            "match": m.group(0),
                            "snippet": f"...{snippet}..."
                        })
                    break

        results[entity_name] = matches

    print("\n" + "-" * 80)
    print("AUDIT RESULTS PER ENTITY")
    print("-" * 80)

    present_count = 0
    missing_count = 0

    for entity_name, matches in results.items():
        print(f"\nEntity: [{entity_name}]")
        if not matches:
            missing_count += 1
            print("  STATUS: Knowledge Base Missing Information")
            print("  Reason: No matching chunks found anywhere in indexed knowledge base.")
        else:
            present_count += 1
            print(f"  STATUS: Present in Knowledge Base ({len(matches)} chunk matches)")
            for i, m in enumerate(matches[:2]):
                print(f"    Match {i+1}: Source='{m['source']}' | Title='{m['title']}'")
                print(f"            Snippet: {m['snippet']}")

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY REPORT")
    print("=" * 80)
    print(f"Total Entities Audited: {len(AUDIT_ENTITIES)}")
    print(f"Entities Present:       {present_count}")
    print(f"Entities Missing:       {missing_count}")
    print("=" * 80)

if __name__ == "__main__":
    main()
