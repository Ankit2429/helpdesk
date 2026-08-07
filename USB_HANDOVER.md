# Campus Helpdesk Robot — USB Transfer & Developer Handover Guide

This repository bundle contains the complete, self-contained **Campus Helpdesk Autonomous AI Robot** codebase, pre-built FAISS vector stores, pre-cached Piper TTS models, canonical markdown knowledge bases, unit/integration test suites, and hardware control scripts.

---

## 1. Fast Setup Guide (For Receiving Developer)

### Option A: Running on Windows / Desktop Workstation (Development Mode)

1. **Extract/Copy Repository:**
   Copy this bundle folder to your working directory.

2. **Setup Python Environment:**
   Requires Python 3.11+. We recommend `uv` or standard Python `venv`:
   ```powershell
   # Using uv (Recommended - fast)
   uv venv .venv
   uv sync --group dev

   # OR using standard pip
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Verify Local Ollama LLM:**
   Ensure Ollama is running locally with the `qwen2.5:3b` model:
   ```powershell
   ollama pull qwen2.5:3b
   ollama run qwen2.5:3b "Who is the Chancellor of KLE Tech?"
   ```

4. **Run Developer Desktop GUI:**
   ```powershell
   python helpdesk_gui.py
   ```
   *Features:* Push-To-Talk microphone support, latency breakdown panel, robot FSM state viewer.

5. **Run FastAPI Server (Kiosk / Web UI):**
   ```powershell
   uvicorn campus_helpdesk.main:app --app-dir src --reload --port 8000
   ```

---

### Option B: Deploying on Raspberry Pi 4 / 5 (Linux ARM64 Production)

1. **Copy Repository to Pi:**
   Transfer the folder to `/home/pi/campus-helpdesk`.

2. **Automated End-to-End Setup Script:**
   Run the automated setup script which installs system packages, sets up Python `.venv`, builds systemd background services, and pre-caches models:
   ```bash
   chmod +x deployment/scripts/setup_pi_deployment.sh
   ./deployment/scripts/setup_pi_deployment.sh
   ```

3. **Start Production Background Service:**
   ```bash
   sudo systemctl start campus-helpdesk-robot
   journalctl -u campus-helpdesk-robot -f
   ```

4. **Full Pi Deployment Guide:**
   See [RASPBERRY_PI_DEPLOYMENT_GUIDE.md](file:///d:/helpdesk/RASPBERRY_PI_DEPLOYMENT_GUIDE.md) for detailed hardware pinouts, ALSA microphone configuration, and offline operation tips.

---

## 2. Verification Checklist

Run these commands to confirm your environment is 100% healthy:

```powershell
# 1. Run Complete Automated Test Suite (270+ unit and integration tests)
pytest tests/ -q

# 2. Test Offline RAG Pipeline Search
python -c "from campus_helpdesk.infrastructure.rag.factory import create_rag_pipeline; from campus_helpdesk.config.settings import get_settings; pipe = create_rag_pipeline(get_settings()); pipe.load_index(); print(pipe.search('library hours'))"

# 3. Test Full Voice Loop (Simulation Mode - No Mic Needed)
python scripts/voice_loop.py --simulate
```

---

## 3. Project Architecture At A Glance

- `src/campus_helpdesk/`: Core active codebase (Clean / Hexagonal Architecture)
  - `application/`: RAG orchestrator, query rewriter, session manager
  - `domain/`: Memory models, knowledge types, confidence scoring rules
  - `infrastructure/`: Hybrid retriever (FAISS + BM25), Ollama adapter, Piper TTS backend
  - `interaction/`: EventBus, Robot FSM, state transitions
  - `runtime/`: SystemRuntime hardware orchestrator
- `data/faiss/`: Persistent vector store index files
- `data/piper/`: Offline Piper TTS voice models (`.onnx`)
- `data/canonical_markdown/`: Cleaned, validated campus knowledge documents
- `deployment/`: systemd unit files and automated Pi deployment bash scripts

---

## 4. Key Developer Commands

| Task | Command |
|------|---------|
| Desktop Developer GUI | `python helpdesk_gui.py` |
| Autonomous Robot Loop CLI | `python -m campus_helpdesk.robot_main --mock` |
| Web API & Kiosk UI | `uvicorn campus_helpdesk.main:app --app-dir src` |
| Rebuild FAISS Vector Index | `python -m campus_helpdesk.ingest` |
| Run Test Suite | `pytest tests/ -v` |
| Create USB Transfer Bundle | `python scripts/bundle_for_transfer.py --zip` |
