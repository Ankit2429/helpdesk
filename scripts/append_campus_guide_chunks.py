"""
append_campus_guide_chunks.py
Converts campus_guide_canonical.md into semantic chunks, appends them to chunks.jsonl,
and rebuilds the production FAISS index at data/faiss and college_faiss_index.
"""

import sys
import json
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.domain.knowledge import KnowledgeDocument
from campus_helpdesk.infrastructure.rag.faiss_store import FAISSSimilarityStore
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

def main():
    guide_path = Path("data/canonical_markdown/facilities/campus_guide_canonical.md")
    if not guide_path.exists():
        print(f"Error: {guide_path} does not exist.")
        return

    content = guide_path.read_text(encoding="utf-8")
    
    # Create chunks for each section
    sections = content.split("## ")
    new_chunks = []
    
    source_rel = "facilities/campus_guide_canonical.md"
    title = "Official Campus Guide & Key Locations"
    category = "Facilities & Campus"
    
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        lines = sec.splitlines()
        heading = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        
        chunk_text = f"### {heading}\n{body}" if body else heading
        
        chunk_item = {
            "chunk_id": str(uuid.uuid4()),
            "source": source_rel,
            "title": title,
            "category": category,
            "subcategory": "Campus Guide",
            "department": "Administration",
            "campus": "Hubballi",
            "document_type": "Campus Guide",
            "headings": [heading],
            "text": chunk_text,
            "word_count": len(chunk_text.split())
        }
        new_chunks.append(chunk_item)
        
    print(f"Generated {len(new_chunks)} semantic chunks for campus_guide_canonical.md.")
    
    # 1. Rewrite chunks.jsonl removing previous campus_guide_canonical entries
    chunks_jsonl_path = Path("chunks.jsonl")
    existing_lines = []
    if chunks_jsonl_path.exists():
        with open(chunks_jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    if item.get("source") != source_rel:
                        existing_lines.append(line.strip())
                        
    with open(chunks_jsonl_path, "w", encoding="utf-8") as f:
        for line in existing_lines:
            f.write(line + "\n")
        for chunk in new_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"Updated chunks.jsonl with {len(new_chunks)} fresh campus_guide_canonical chunks (total chunks: {len(existing_lines) + len(new_chunks)}).")
    
    # 2. Rebuild FAISS index at data/faiss and college_faiss_index
    settings = Settings()
    docs = []
    with open(chunks_jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                text = item.get("text", "")
                if not text.strip():
                    continue
                metadata = {
                    "source": str(item.get("source", "")),
                    "title": str(item.get("title", "")),
                    "category": str(item.get("category", "")),
                    "subcategory": str(item.get("subcategory", "")),
                    "department": str(item.get("department", "")),
                    "campus": str(item.get("campus", "")),
                    "document_type": str(item.get("document_type", "")),
                    "headings": ", ".join(item.get("headings", [])) if isinstance(item.get("headings"), list) else str(item.get("headings", "")),
                }
                docs.append(KnowledgeDocument(content=text, metadata=metadata))
                
    print(f"Total knowledge documents loaded from chunks.jsonl: {len(docs)}")
    
    embeddings = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=True,
        local_files_only=settings.embedding_local_files_only,
    )
    
    # Update data/faiss
    faiss_path = Path("data/faiss")
    faiss_store = FAISSSimilarityStore(
        embeddings=embeddings,
        index_path=faiss_path,
        allow_dangerous_deserialization=True,
        embedding_metadata={
            "embedding_model": settings.embedding_model,
            "embedding_normalize": settings.embedding_normalize,
        },
    )
    faiss_store.add(docs)
    faiss_store.save()
    print("Rebuilt FAISS store at data/faiss successfully!")
    
    # Update college_faiss_index as well if present
    c_faiss_path = Path("college_faiss_index")
    if c_faiss_path.exists():
        c_faiss_store = FAISSSimilarityStore(
            embeddings=embeddings,
            index_path=c_faiss_path,
            allow_dangerous_deserialization=True,
            embedding_metadata={
                "embedding_model": settings.embedding_model,
                "embedding_normalize": settings.embedding_normalize,
            },
        )
        c_faiss_store.add(docs)
        c_faiss_store.save()
        print("Rebuilt FAISS store at college_faiss_index successfully!")

if __name__ == "__main__":
    main()
