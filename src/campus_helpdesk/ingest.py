"""Standalone FAISS ingestion script for campus knowledge (PDFs + website links)."""

import os
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
try:
    vectordb.save_local(str(ALT_INDEX_PATH))
except Exception:
    pass

print(f"\n[SUCCESS] FAISS index successfully created and saved to '{FAISS_INDEX_PATH}'!")
print("When you launch 'demo.py', it will automatically load this campus knowledge.")