# Campus Helpdesk — Deployment Guide

Complete guide for first-time setup, running, troubleshooting, and packaging the Campus Helpdesk Robot application on Windows.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Required Software](#2-required-software)
3. [Clone and Install Dependencies](#3-clone-and-install-dependencies)
4. [Configure Environment](#4-configure-environment)
5. [Install and Start Ollama](#5-install-and-start-ollama)
6. [Download the LLM Model](#6-download-the-llm-model)
7. [Ingest PDF Knowledge Base](#7-ingest-pdf-knowledge-base)
8. [Run the FastAPI API Server](#8-run-the-fastapi-api-server)
9. [Run the Desktop GUI](#9-run-the-desktop-gui)
10. [Ollama Memory Tuning](#10-ollama-memory-tuning)
11. [Troubleshooting](#11-troubleshooting)
12. [Package for Windows (PyInstaller)](#12-package-for-windows-pyinstaller)
13. [Auto-Start on Login](#13-auto-start-on-login)
14. [Deploying on Another Windows Laptop](#14-deploying-on-another-windows-laptop)

---

## 1. System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 64-bit | Windows 11 64-bit |
| **RAM** | 8 GB | 16 GB |
| **Free RAM at runtime** | 5 GB | 8 GB+ |
| **CPU** | 4 cores | 6+ cores (e.g. Ryzen 5 5600H) |
| **Storage** | 10 GB free | 20 GB free |
| **Webcam** | Optional | USB or built-in for person detection |
| **Microphone** | Optional | Required for voice input |
| **Internet** | Not required at runtime | Required only at first install |

> Runs fully offline after first-time setup.

---

## 2. Required Software

| Software | Download URL | Notes |
|---|---|---|
| **Python 3.11+** | https://python.org | Tick "Add Python to PATH" during install |
| **uv** (package manager) | https://docs.astral.sh/uv/ | Run: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` |
| **Git** | https://git-scm.com | Required to clone the repository |
| **Ollama** | https://ollama.com/download/windows | Required to run the local LLM |
| **Microsoft Visual C++ Redistributable** | https://aka.ms/vs/17/release/vc_redist.x64.exe | Required for some Python packages |

---

## 3. Clone and Install Dependencies

```powershell
git clone https://github.com/Ankit2429/helpdesk.git
cd helpdesk
uv sync
```

`uv sync` reads `pyproject.toml` and installs all dependencies into `.venv` automatically.

---

## 4. Configure Environment

```powershell
Copy-Item .env.example .env
```

Open `.env` and set at minimum:

```dotenv
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434
```

### Key Configuration Parameters

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | *(required)* | The Ollama model tag to use |
| `OLLAMA_CONTEXT_WINDOW` | `2048` | KV cache size in tokens. Lower = less RAM. |
| `OLLAMA_MAX_OUTPUT_TOKENS` | `512` | Maximum tokens per response |
| `OLLAMA_NUM_THREADS` | `6` | CPU threads. Set to your physical core count. |
| `OLLAMA_TEMPERATURE` | `0.2` | Response randomness (0.0 = deterministic) |

IMPORTANT: `OLLAMA_CONTEXT_WINDOW=2048` is the safe default for 16 GB RAM with other apps running.
Increasing beyond 4096 on low free RAM causes `failed to allocate CPU buffer` crashes.

---

## 5. Install and Start Ollama

1. Download and install Ollama from https://ollama.com/download/windows
2. Ollama starts automatically as a background Windows service.
3. Verify it is running:

```powershell
ollama list
```

---

## 6. Download the LLM Model

```powershell
ollama pull qwen2.5:7b
ollama list
```

### Alternative Models (if qwen2.5:7b is too large)

| Model | RAM Required | Quality | Command |
|---|---|---|---|
| `qwen2.5:7b` | ~5 GB | Best | `ollama pull qwen2.5:7b` |
| `qwen2.5:3b` | ~2.5 GB | Good | `ollama pull qwen2.5:3b` |
| `qwen2.5:1.5b` | ~1.5 GB | Fast | `ollama pull qwen2.5:1.5b` |
| `phi3:mini` | ~2.3 GB | Good | `ollama pull phi3:mini` |
| `gemma2:2b` | ~1.6 GB | Good | `ollama pull gemma2:2b` |

To switch models, change `OLLAMA_MODEL=qwen2.5:3b` in `.env`. No source code changes needed.

---

## 7. Ingest PDF Knowledge Base

Place PDF files into `data/knowledge/`:

```
data/
  knowledge/
    library.pdf
    departments.pdf
    schedule.pdf
```

Then build the FAISS vector index:

```powershell
uv run python -m campus_helpdesk.scripts.ingest
```

Only needs to run when you add or update PDF documents.

---

## 8. Run the FastAPI API Server

```powershell
uv run uvicorn campus_helpdesk.main:app --app-dir src --host 127.0.0.1 --port 8000
```

- **Chat endpoint**: http://localhost:8000/chat
- **Health check**: http://localhost:8000/health
- **Interactive docs**: http://localhost:8000/docs

---

## 9. Run the Desktop GUI

```powershell
uv run python -m campus_helpdesk.demo
```

The GUI opens with:
- Live webcam feed with person detection overlay
- Chat interface with text input and Mic button
- Status bar (IDLE / LISTENING / SPEAKING)

### Using the Mic Button
1. Click **Mic**
2. Speak your question clearly
3. Transcript appears in chat and robot responds

---

## 10. Ollama Memory Tuning

### Common Crash: `failed to allocate CPU buffer`

Cause: Not enough free RAM for the LLM KV cache.

### Context Window vs RAM Usage (qwen2.5:7b)

| OLLAMA_CONTEXT_WINDOW | KV Cache RAM | Total RAM Needed |
|---|---|---|
| 8192 | ~1.2 GB | ~5.9 GB |
| 4096 | ~600 MB | ~5.3 GB |
| 2048 (default) | ~300 MB | ~5.0 GB |
| 1024 | ~150 MB | ~4.85 GB |

### RAM Quick Reference

| Free RAM | Recommended Setting |
|---|---|
| < 4 GB | `OLLAMA_CONTEXT_WINDOW=1024` + switch to `qwen2.5:1.5b` |
| 4–6 GB | `OLLAMA_CONTEXT_WINDOW=2048` (default) |
| 6–10 GB | `OLLAMA_CONTEXT_WINDOW=4096` |
| 10+ GB | `OLLAMA_CONTEXT_WINDOW=8192` |

Check free RAM:
```powershell
(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
```

---

## 11. Troubleshooting

### `failed to allocate CPU buffer`
Reduce context window in `.env`:
```dotenv
OLLAMA_CONTEXT_WINDOW=2048
```
Or switch to a smaller model: `OLLAMA_MODEL=qwen2.5:3b`

### `DLL load failed: An Application Control policy has blocked this file`
Already handled — the app uses PyTorch HuggingFace Whisper which requires no native C++ DLLs.

### `CUDA error: shared object initialization failed`
Already handled — `num_gpu: 0` is set in settings.py to force CPU-only mode.

### `Could not hear any speech` after clicking Mic
1. Check Windows microphone permissions: Settings > Privacy > Microphone
2. Right-click speaker icon > Sound Settings > Input — confirm correct mic is selected
3. If FxSound is installed, the app automatically bypasses it to use Realtek hardware mic
4. Run isolated mic test:
```powershell
uv run python -c "
from campus_helpdesk.infrastructure.audio.stt_service import FasterWhisperSTTService
stt = FasterWhisperSTTService()
result = stt.listen_and_transcribe()
print('RESULT:', repr(result))
"
```

### `Ollama connection refused` (port 11434)
Start Ollama manually:
```powershell
ollama serve
```

### FAISS index not found
Run PDF ingestion:
```powershell
uv run python -m campus_helpdesk.scripts.ingest
```

### `ModuleNotFoundError: No module named faiss.swigfaiss_avx2`
Safe to ignore — FAISS loads the non-AVX2 build which works correctly on all CPUs.

---

## 12. Package for Windows (PyInstaller)

```powershell
uv add --dev pyinstaller

uv run pyinstaller `
  --onefile `
  --windowed `
  --name "CampusHelpdesk" `
  --add-data "data;data" `
  --add-data "src;src" `
  --paths src `
  src/campus_helpdesk/__main__.py
```

The executable will be at `dist/CampusHelpdesk.exe`.

NOTE: The `.exe` still requires Ollama running as a background service.

---

## 13. Auto-Start on Login

### Option A: Windows Task Scheduler (Recommended)

1. Open Task Scheduler > Create Task
2. General tab > Name: `Campus Helpdesk Demo`
3. Triggers > New > At log on
4. Actions > New > Program: `powershell.exe` > Arguments:
```
-WindowStyle Hidden -Command "cd 'D:\helpdesk\anti'; uv run python -m campus_helpdesk.demo"
```
5. Settings > Allow task to be run on demand

### Option B: Startup Folder

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\CampusHelpdesk.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -Command `"cd 'D:\helpdesk\anti'; uv run python -m campus_helpdesk.demo`""
$Shortcut.WorkingDirectory = "D:\helpdesk\anti"
$Shortcut.Save()
```

---

## 14. Deploying on Another Windows Laptop

No source code changes are required. All configuration is through `.env`.

### Steps

```powershell
# 1. Clone
git clone https://github.com/Ankit2429/helpdesk.git
cd helpdesk

# 2. Install uv (from https://astral.sh/uv)

# 3. Install dependencies
uv sync

# 4. Install Ollama (from https://ollama.com/download/windows)

# 5. Pull model
ollama pull qwen2.5:7b

# 6. Configure
Copy-Item .env.example .env
# Edit .env to set OLLAMA_MODEL and tune OLLAMA_CONTEXT_WINDOW for your RAM

# 7. Ingest PDFs (if not using pre-built FAISS index)
uv run python -m campus_helpdesk.scripts.ingest

# 8. Run
uv run python -m campus_helpdesk.demo
```

### RAM Configuration Quick Reference

| Available RAM | Suggested Model | OLLAMA_CONTEXT_WINDOW |
|---|---|---|
| 8 GB | `qwen2.5:3b` | `1024` |
| 12 GB | `qwen2.5:7b` | `1024` |
| 16 GB (4 GB free) | `qwen2.5:7b` | `2048` |
| 16 GB (8 GB free) | `qwen2.5:7b` | `4096` |
| 32 GB | `qwen2.5:7b` | `8192` |

TIP: Close Chrome, VS Code, and other apps before running the demo on low-RAM machines.
