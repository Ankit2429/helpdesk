"""Standalone FAISS ingestion script for campus knowledge (PDFs + website links)."""

import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# ---- CONFIG ----
PDF_FOLDER = "./pdfs"              # folder containing your college PDFs
URLS = [
    "https://yourcollege.edu.in/admissions",
    "https://yourcollege.edu.in/departments/ise",
]
FAISS_INDEX_PATH = "./college_faiss_index"   # where the index gets saved
EMBED_MODEL = "all-MiniLM-L6-v2"

# ---- 1. LOAD DOCUMENTS ----
all_docs = []

if os.path.isdir(PDF_FOLDER):
    pdf_loader = DirectoryLoader(PDF_FOLDER, glob="**/*.pdf", loader_cls=PyPDFLoader)
    pdf_docs = pdf_loader.load()
    print(f"Loaded {len(pdf_docs)} pages from PDFs")
    all_docs += pdf_docs
else:
    print(f"PDF folder not found: {PDF_FOLDER}")

if URLS:
    web_loader = WebBaseLoader(URLS)
    web_docs = web_loader.load()
    print(f"Loaded {len(web_docs)} pages from websites")
    all_docs += web_docs

if not all_docs:
    print("No documents loaded. Check your PDF_FOLDER and URLS.")
    exit()

# ---- 2. CHUNK ----
splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
chunks = splitter.split_documents(all_docs)
print(f"Split into {len(chunks)} chunks")

# ---- 3. EMBED + BUILD FAISS INDEX ----
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

if os.path.exists(FAISS_INDEX_PATH):
    # Load existing index and add new chunks to it
    print("Existing FAISS index found — loading and updating it")
    vectordb = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    vectordb.add_documents(chunks)
else:
    # First-time creation
    print("No existing index — creating a new one")
    vectordb = FAISS.from_documents(chunks, embeddings)

# ---- 4. SAVE ----
vectordb.save_local(FAISS_INDEX_PATH)
print(f"FAISS index saved to {FAISS_INDEX_PATH}")