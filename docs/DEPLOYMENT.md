# Offline Campus Helpdesk Robot — Production Deployment Guide

## Overview

This guide describes how to deploy the **Offline AI Campus Helpdesk Robot** backend and desktop application in a zero-connectivity environment.

---

## Hardware & System Requirements

- **Operating System**: Windows 10/11 or Ubuntu Linux 22.04 LTS (x86_64)
- **CPU**: Intel Core i5/i7 (8th Gen or higher) / AMD Ryzen 5/7
- **RAM**: Minimum 16 GB DDR4/DDR5
- **Storage**: 20 GB free disk space (SSD recommended)
- **Peripherals**: USB Webcam (720p/1080p), USB Microphone, Speakers

---

## Pre-Deployment Checklist (Offline Assets)

Before bringing the hardware to an offline environment, ensure the following local assets are cached:

1. **Python Virtual Environment**:
   - Python 3.11 with pre-installed wheels via `uv`.
2. **Ollama LLM Model**:
   - Ollama server installed with the `qwen2.5:7b` model tag pulled.
3. **Embedding Model**:
   - `sentence-transformers/all-MiniLM-L6-v2` downloaded into HuggingFace local cache.
4. **Faster-Whisper Model**:
   - Faster-Whisper `base` or `tiny` model cached locally.

---

## Deployment Modes

### Mode 1: Interactive Desktop Robot Kiosk (GUI Application)

```powershell
# 1. Start Ollama Local Service
ollama serve

# 2. Ingest Campus PDF Documents into FAISS Index
uv run python -m campus_helpdesk.ingest

# 3. Launch Interactive Desktop Application
uv run python -m campus_helpdesk.demo
```

### Mode 2: Headless Production Web API Service (FastAPI)

```powershell
# 1. Start Ollama Local Service
ollama serve

# 2. Ingest Campus PDF Documents
uv run python -m campus_helpdesk.ingest

# 3. Start Production Uvicorn Server
uv run uvicorn campus_helpdesk.main:app --app-dir src --host 0.0.0.0 --port 8000 --workers 4
```

---

## Production Logs

Logs are stored locally with daily rotation under `logs/`:
- Format: `logs/YYYY-MM-DD.log`
- Retention: 30 days automated cleanup.
