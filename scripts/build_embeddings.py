#!/usr/bin/env python3
"""
build_embeddings.py
===================
Generates vector embeddings for all retrieval chunks in chunks.jsonl, builds a FAISS index,
persists outputs to embeddings.faiss and embedding_metadata.jsonl, and logs stats in embedding_report.json.
"""

import os
import sys
import json
import time
import uuid
import numpy as np
import faiss

# Add src/ folder to sys.path to allow imports from campus_helpdesk
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from campus_helpdesk.config.settings import Settings
from campus_helpdesk.infrastructure.rag.sentence_transformer_embeddings import SentenceTransformerEmbeddings

def main():
    start_time = time.time()
    workspace_root = r"d:\helpdesk\anti"
    chunks_jsonl_path = os.path.join(workspace_root, "chunks.jsonl")
    
    if not os.path.exists(chunks_jsonl_path):
        print(f"Error: {chunks_jsonl_path} not found. Run semantic_chunker.py first.")
        sys.exit(1)
        
    print("Reading chunks from chunks.jsonl...")
    chunks = []
    with open(chunks_jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
                
    print(f"Loaded {len(chunks)} chunks.")
    
    # Validation trackers
    duplicate_ids = 0
    empty_chunks = 0
    failed_embeddings = 0
    
    seen_ids = set()
    texts_to_embed = []
    valid_chunks = []
    
    for idx, chunk in enumerate(chunks):
        chunk_id = chunk.get("id")
        text = chunk.get("text", "")
        
        # Check duplicate IDs
        if chunk_id in seen_ids:
            duplicate_ids += 1
            # Generate a new unique ID to keep it valid
            chunk_id = str(uuid.uuid4())
            chunk["id"] = chunk_id
        seen_ids.add(chunk_id)
        
        # Check empty chunks
        if not text.strip():
            empty_chunks += 1
            continue
            
        texts_to_embed.append(text)
        valid_chunks.append(chunk)
        
    # Load embedding model settings
    settings = Settings()
    print(f"Initializing embedding model: {settings.embedding_model}...")
    embedding_adapter = SentenceTransformerEmbeddings(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=settings.embedding_normalize,
        show_progress=True,
        local_files_only=settings.embedding_local_files_only,
    )
    
    # Generate embeddings
    print(f"Generating embeddings for {len(texts_to_embed)} text blocks...")
    try:
        embeddings_list = embedding_adapter.embed_documents(texts_to_embed)
    except Exception as e:
        print(f"Error during embedding generation: {e}")
        failed_embeddings = len(texts_to_embed)
        embeddings_list = []
        
    if not embeddings_list:
        print("Error: No embeddings were generated.")
        sys.exit(1)
        
    # Validation checks on vectors
    empty_vectors = 0
    for vec in embeddings_list:
        if not vec or all(v == 0.0 for v in vec):
            empty_vectors += 1
            
    print(f"Successfully generated {len(embeddings_list)} embeddings.")
    
    # Build FAISS index
    embedding_matrix = np.array(embeddings_list, dtype=np.float32)
    dimension = embedding_matrix.shape[1]
    
    print(f"Building FAISS Inner Product index (dimension={dimension})...")
    # Since embeddings are normalized (settings.embedding_normalize=True), 
    # IndexFlatIP (Inner Product) is equivalent to cosine similarity.
    index = faiss.IndexFlatIP(dimension)
    index.add(embedding_matrix)
    
    # Save index
    faiss_output_path = os.path.join(workspace_root, "embeddings.faiss")
    print(f"Saving FAISS index to {faiss_output_path}...")
    faiss.write_index(index, faiss_output_path)
    
    # Save embedding_metadata.jsonl
    metadata_jsonl_path = os.path.join(workspace_root, "embedding_metadata.jsonl")
    print(f"Saving metadata and embeddings to {metadata_jsonl_path}...")
    
    with open(metadata_jsonl_path, "w", encoding="utf-8") as f_meta:
        for idx, chunk in enumerate(valid_chunks):
            # Extract inherited metadata properties
            metadata_dict = {
                "title": chunk.get("title", ""),
                "category": chunk.get("category", ""),
                "subcategory": chunk.get("subcategory", ""),
                "department": chunk.get("department", ""),
                "campus": chunk.get("campus", ""),
                "document_type": chunk.get("document_type", ""),
                "source_url": chunk.get("source_url", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "headings": chunk.get("headings", []),
                "source": chunk.get("source", "")
            }
            
            meta_line = {
                "id": chunk["id"],
                "text": chunk["text"],
                "metadata": metadata_dict,
                "embedding": embeddings_list[idx]
            }
            f_meta.write(json.dumps(meta_line) + "\n")
            
    elapsed_time = time.time() - start_time
    
    # Generate embedding_report.json
    report_path = os.path.join(workspace_root, "embedding_report.json")
    report_data = {
        "chunks_embedded": len(embeddings_list),
        "embedding_dimension": dimension,
        "duplicates": duplicate_ids,
        "empty_chunks": empty_chunks,
        "empty_vectors": empty_vectors,
        "failed_embeddings": failed_embeddings,
        "elapsed_time": round(elapsed_time, 2)
    }
    
    with open(report_path, "w", encoding="utf-8") as r_file:
        json.dump(report_data, r_file, indent=2)
        
    print("\n=========================================")
    print("      EMBEDDINGS GENERATION SUMMARY")
    print("=========================================")
    print(f"Chunks Embedded        : {len(embeddings_list)}")
    print(f"Embedding Dimension    : {dimension}")
    print(f"Duplicate Chunk IDs    : {duplicate_ids}")
    print(f"Empty Chunks Encountered: {empty_chunks}")
    print(f"Empty Vectors Found    : {empty_vectors}")
    print(f"Failed Embeddings      : {failed_embeddings}")
    print(f"Elapsed Time           : {round(elapsed_time, 2)} seconds")
    print(f"FAISS Index Saved      : {faiss_output_path}")
    print(f"Metadata JSONL Saved   : {metadata_jsonl_path}")
    print(f"Report JSON Generated  : {report_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
