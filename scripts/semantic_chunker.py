#!/usr/bin/env python3
"""
semantic_chunker.py
===================
Converts cleaned markdown documents with YAML front matter into high-quality semantic chunks,
saving chunks in chunks.jsonl and statistics in chunk_report.json.
"""

import os
import sys
import json
import re
import uuid

def parse_yaml(yaml_text):
    meta = {}
    for line in yaml_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            elif v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            if v.startswith("[") and v.endswith("]"):
                try:
                    v = json.loads(v)
                except:
                    pass
            meta[k] = v
    return meta

def split_into_segments(body_text):
    lines = body_text.splitlines()
    
    segments = []
    current_headings = ["", "", "", ""] # representing H1, H2, H3, H4
    
    # We accumulate lines into a buffer
    buffer = []
    buffer_type = "text" # "text", "table", "list"
    
    def flush_buffer():
        if not buffer:
            return
        text_content = "\n".join(buffer).strip()
        if text_content:
            active_headings = [h for h in current_headings if h]
            segments.append({
                "headings": active_headings,
                "text": text_content,
                "type": buffer_type,
                "word_count": len(text_content.split())
            })
        buffer.clear()

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_strip = line.strip()
        
        # 1. Check for headings
        heading_match = re.match(r"^(#+)\s+(.*)", line_strip)
        if heading_match:
            flush_buffer()
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            if level == 1:
                current_headings = [heading_text, "", "", ""]
            elif level == 2:
                current_headings = [current_headings[0], heading_text, "", ""]
            elif level == 3:
                current_headings = [current_headings[0], current_headings[1], heading_text, ""]
            elif level >= 4:
                current_headings = [current_headings[0], current_headings[1], current_headings[2], heading_text]
            
            # Put the heading itself into buffer
            buffer_type = "text"
            buffer.append(line)
            idx += 1
            continue
            
        # 2. Check for Table lines
        is_table_line = line_strip.startswith("|") or (line_strip.count("|") >= 2)
        if is_table_line:
            if buffer_type != "table":
                flush_buffer()
                buffer_type = "table"
            buffer.append(line)
            idx += 1
            continue
            
        # 3. Check for List lines
        is_list_line = re.match(r"^\s*([-*+]|\d+\.)\s+", line_strip)
        if is_list_line:
            if buffer_type != "list" and buffer_type != "table":
                flush_buffer()
                buffer_type = "list"
            buffer.append(line)
            idx += 1
            continue
            
        # 4. Standard text/paragraph line
        if not line_strip:
            # Empty line can separate paragraphs, but keep lists/tables together
            if buffer_type in ("table", "list"):
                # Check if next line continues table/list
                next_is_same = False
                if idx + 1 < len(lines):
                    next_line_strip = lines[idx + 1].strip()
                    if buffer_type == "table" and (next_line_strip.startswith("|") or next_line_strip.count("|") >= 2):
                        next_is_same = True
                    elif buffer_type == "list" and re.match(r"^\s*([-*+]|\d+\.)\s+", next_line_strip):
                        next_is_same = True
                
                if next_is_same:
                    buffer.append(line)
                    idx += 1
                    continue
                else:
                    flush_buffer()
                    buffer_type = "text"
            else:
                buffer.append(line)
        else:
            if buffer_type != "text":
                flush_buffer()
                buffer_type = "text"
            buffer.append(line)
            
        idx += 1
        
    flush_buffer()
    return segments

def main():
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    markdown_root = os.path.normpath(os.path.join(workspace_root, "data", "canonical_markdown"))
    
    if not os.path.exists(markdown_root):
        print(f"Error: Markdown root path '{markdown_root}' does not exist.")
        sys.exit(1)
        
    jsonl_output_path = os.path.join(workspace_root, "chunks.jsonl")
    report_json_path = os.path.join(workspace_root, "chunk_report.json")
    
    documents_processed = 0
    chunks_generated = 0
    total_words = 0
    largest_chunk_words = 0
    smallest_chunk_words = 999999
    merged_sections_count = 0
    tables_preserved_count = 0
    error_count = 0
    
    # Open jsonl file for writing chunks
    with open(jsonl_output_path, "w", encoding="utf-8") as jsonl_file:
        for root, dirs, files in os.walk(markdown_root):
            for f in files:
                if f.endswith(".md"):
                    fp = os.path.join(root, f)
                    rel_path = os.path.relpath(fp, markdown_root)
                    rel_path_unix = rel_path.replace(os.sep, "/")
                    
                    try:
                        with open(fp, encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                            
                        # Parse YAML front matter
                        yaml_meta = {}
                        body_text = content
                        if content.strip().startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                yaml_meta = parse_yaml(parts[1])
                                body_text = parts[2]
                                
                        # Extract chunks dynamically
                        segments = split_into_segments(body_text)
                        
                        doc_chunks = []
                        current_chunk_segments = []
                        current_words = 0
                        
                        for seg in segments:
                            if seg["type"] == "table":
                                tables_preserved_count += 1
                                
                            seg_words = seg["word_count"]
                            
                            # If adding this segment exceeds our soft target max (800 words)
                            if current_words + seg_words > 800:
                                if current_chunk_segments:
                                    # Flush current chunk
                                    chunk_text = "\n\n".join([s["text"] for s in current_chunk_segments])
                                    # Collect headings (union of headings of constituent segments)
                                    chunk_headings = []
                                    seen_h = set()
                                    for s in current_chunk_segments:
                                        for h in s["headings"]:
                                            if h not in seen_h:
                                                seen_h.add(h)
                                                chunk_headings.append(h)
                                                
                                    doc_chunks.append({
                                        "text": chunk_text,
                                        "headings": chunk_headings,
                                        "word_count": current_words
                                    })
                                    current_chunk_segments = [seg]
                                    current_words = seg_words
                                else:
                                    # Single segment is > 800 words
                                    doc_chunks.append({
                                        "text": seg["text"],
                                        "headings": seg["headings"],
                                        "word_count": seg_words
                                    })
                                    current_chunk_segments = []
                                    current_words = 0
                            else:
                                current_chunk_segments.append(seg)
                                current_words += seg_words
                                
                        # Flush the last chunk
                        if current_chunk_segments:
                            chunk_text = "\n\n".join([s["text"] for s in current_chunk_segments])
                            chunk_headings = []
                            seen_h = set()
                            for s in current_chunk_segments:
                                for h in s["headings"]:
                                    if h not in seen_h:
                                        seen_h.add(h)
                                        chunk_headings.append(h)
                            
                            chunk_word_count = current_words
                            
                            # Check if the final chunk is too small (< 100 words) and we have previous chunks
                            if chunk_word_count < 100 and doc_chunks:
                                # Merge with the last chunk
                                last_chunk = doc_chunks[-1]
                                last_chunk["text"] += "\n\n" + chunk_text
                                for h in chunk_headings:
                                    if h not in last_chunk["headings"]:
                                        last_chunk["headings"].append(h)
                                last_chunk["word_count"] += chunk_word_count
                                merged_sections_count += 1
                            else:
                                doc_chunks.append({
                                    "text": chunk_text,
                                    "headings": chunk_headings,
                                    "word_count": chunk_word_count
                                })
                                
                        # Write the chunks to JSONL
                        for c_idx, chunk in enumerate(doc_chunks):
                            chunk_id = str(uuid.uuid4())
                            
                            # Combine chunk data with inherited YAML metadata
                            chunk_data = {
                                "id": chunk_id,
                                "source": rel_path_unix,
                                "title": yaml_meta.get("title", ""),
                                "category": yaml_meta.get("category", ""),
                                "subcategory": yaml_meta.get("subcategory", ""),
                                "department": yaml_meta.get("department", ""),
                                "campus": yaml_meta.get("campus", ""),
                                "document_type": yaml_meta.get("document_type", ""),
                                "source_url": yaml_meta.get("source_url", ""),
                                "chunk_index": c_idx,
                                "text": chunk["text"],
                                "headings": chunk["headings"]
                            }
                            
                            jsonl_file.write(json.dumps(chunk_data) + "\n")
                            chunks_generated += 1
                            
                            w_count = chunk["word_count"]
                            total_words += w_count
                            if w_count > largest_chunk_words:
                                largest_chunk_words = w_count
                            if w_count < smallest_chunk_words:
                                smallest_chunk_words = w_count
                                
                        documents_processed += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to chunk {rel_path}: {e}")
                        error_count += 1
                        
    # Write chunk_report.json
    average_chunk_size = (total_words / chunks_generated) if chunks_generated > 0 else 0
    if smallest_chunk_words == 999999:
        smallest_chunk_words = 0
        
    try:
        with open(report_json_path, "w", encoding="utf-8") as rf:
            json.dump({
                "documents_processed": documents_processed,
                "chunks_generated": chunks_generated,
                "average_chunk_size": round(average_chunk_size, 2),
                "largest_chunk": largest_chunk_words,
                "smallest_chunk": smallest_chunk_words,
                "merged_sections": merged_sections_count,
                "tables_preserved": tables_preserved_count,
                "errors": error_count
            }, rf, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to write report: {e}")
        error_count += 1
        
    print("\n=========================================")
    print("      SEMANTIC CHUNKER SUMMARY")
    print("=========================================")
    print(f"Documents Processed    : {documents_processed}")
    print(f"Chunks Generated       : {chunks_generated}")
    print(f"Average Chunk Size     : {round(average_chunk_size, 2)} words")
    print(f"Largest Chunk          : {largest_chunk_words} words")
    print(f"Smallest Chunk         : {smallest_chunk_words} words")
    print(f"Merged Sections        : {merged_sections_count}")
    print(f"Tables Preserved       : {tables_preserved_count}")
    print(f"Errors Encountered     : {error_count}")
    print(f"Chunks JSONL Generated : {jsonl_output_path}")
    print(f"Report JSON Generated  : {report_json_path}")
    print("=========================================\n")

if __name__ == "__main__":
    main()
