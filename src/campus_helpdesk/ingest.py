"""Standalone FAISS ingestion script for campus knowledge (PDFs + website links)."""

import os
import json
import logging
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest")

# ---- CONFIG ----
# Folder paths to look for PDF files
PDF_FOLDERS = [Path("data/knowledge"), Path("pdfs")]

# Website URLs to scrape (Replace with your college URLs)
URLS = [
    # "https://yourcollege.edu.in/admissions",
    # "https://yourcollege.edu.in/departments/ise",
]

# FAISS Vector Index Output Paths (data/faiss is loaded by demo.py)
FAISS_INDEX_PATH = Path("data/faiss")
ALT_INDEX_PATH = Path("college_faiss_index")
EMBED_MODEL = "all-MiniLM-L6-v2"

# ---- 1. LOAD DOCUMENTS ----
all_docs = []

# Ensure directories exist
for folder in PDF_FOLDERS:
    folder.mkdir(parents=True, exist_ok=True)
    if folder.exists():
        try:
            # Load PDFs
            pdf_loader = DirectoryLoader(str(folder), glob="**/*.pdf", loader_cls=PyPDFLoader)
            pdf_docs = pdf_loader.load()
            if pdf_docs:
                logger.info(f"Loaded {len(pdf_docs)} pages from PDFs in '{folder}'")
                all_docs.extend(pdf_docs)

            # Load Text & Markdown files
            from langchain_community.document_loaders import TextLoader
            for ext in ["*.txt", "*.md"]:
                txt_loader = DirectoryLoader(str(folder), glob=f"**/{ext}", loader_cls=TextLoader)
                txt_docs = txt_loader.load()
                if txt_docs:
                    logger.info(f"Loaded {len(txt_docs)} text document(s) ({ext}) from '{folder}'")
                    all_docs.extend(txt_docs)

        except Exception as e:
            logger.warning(f"Error loading files from {folder}: {e}")

# Load Web Pages if configured
valid_urls = [u for u in URLS if "yourcollege.edu.in" not in u and u.startswith("http")]
if valid_urls:
    try:
        os.environ.setdefault("USER_AGENT", "CampusHelpdeskRobot/1.0")
        web_loader = WebBaseLoader(valid_urls)
        web_docs = web_loader.load()
        logger.info(f"Loaded {len(web_docs)} pages from web URLs")
        all_docs.extend(web_docs)
    except Exception as e:
        logger.warning(f"Error loading web URLs: {e}")

if not all_docs:
    print("\n[INFO] No PDF documents or URLs were ingested.")
    print("Please copy your college PDF documents into the 'data/knowledge/' or 'pdfs/' folder.")
    print("Example: Place 'campus_map_guide.pdf' inside 'data/knowledge/' and run this script again.\n")
    exit(0)

# ---- 2. CHUNK ----
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
chunks = splitter.split_documents(all_docs)
print(f"Split into {len(chunks)} text chunks.")

# ---- 3. EMBED + BUILD FAISS INDEX ----
print(f"Loading embedding model '{EMBED_MODEL}'...")
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

# ---- 3.5 DUPLICATE & CONFLICT DETECTION ----
print("\nScanning text chunks for potential topic overlap / factual conflicts...")
chunk_texts = [c.page_content for c in chunks]
chunk_sources = [c.metadata.get("source", f"Chunk #{i+1}") for i, c in enumerate(chunks)]

if len(chunks) > 1:
    import numpy as np
    try:
        raw_embeddings = embeddings.embed_documents(chunk_texts)
        emb_matrix = np.array(raw_embeddings, dtype=np.float32)
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        norm_embeddings = emb_matrix / norms

        similarity_matrix = np.dot(norm_embeddings, norm_embeddings.T)

        conflicts_found = []
        SIMILARITY_THRESHOLD = 0.75

        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                sim = float(similarity_matrix[i, j])
                if sim >= SIMILARITY_THRESHOLD:
                    if chunk_texts[i].strip() != chunk_texts[j].strip():
                        conflicts_found.append({
                            "sim": sim,
                            "source1": chunk_sources[i],
                            "text1": chunk_texts[i][:150].replace("\n", " "),
                            "source2": chunk_sources[j],
                            "text2": chunk_texts[j][:150].replace("\n", " "),
                        })

        if conflicts_found:
            print("\n" + "!" * 80)
            print(f"[WARNING] FLAGGED {len(conflicts_found)} POTENTIAL DUPLICATE/CONFLICT PAIR(S) FOR MANUAL REVIEW:")
            print("!" * 80)
            for idx, conf in enumerate(conflicts_found, 1):
                print(f"\n  Pair #{idx} (Semantic Similarity: {conf['sim']:.2f}):")
                print(f"    Source A [{conf['source1']}]: \"{conf['text1']}...\"")
                print(f"    Source B [{conf['source2']}]: \"{conf['text2']}...\"")
            print("\n" + "!" * 80)
            print("Please review the flagged source documents to prevent conflicting facts!")
            print("!" * 80 + "\n")
        else:
            print("[OK] No conflicting chunk pairs detected.")
    except Exception as exc:
        print(f"Warning during duplicate scan: {exc}")

FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)

if (FAISS_INDEX_PATH / "index.faiss").exists():
    print("Existing FAISS index found — loading and updating it...")
    vectordb = FAISS.load_local(str(FAISS_INDEX_PATH), embeddings, allow_dangerous_deserialization=True)
    vectordb.add_documents(chunks)
else:
    print("Creating new FAISS index...")
    vectordb = FAISS.from_documents(chunks, embeddings)

# ---- 4. SAVE ----
vectordb.save_local(str(FAISS_INDEX_PATH))
manifest_data = {"embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "embedding_normalize": True}
(FAISS_INDEX_PATH / "index-manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
try:
    vectordb.save_local(str(ALT_INDEX_PATH))
    (ALT_INDEX_PATH / "index-manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
except Exception:
    pass

print(f"\n[SUCCESS] FAISS index successfully created and saved to '{FAISS_INDEX_PATH}'!")
print("When you launch 'demo.py', it will automatically load this campus knowledge.")