# Raspberry Pi 4 / 5 Production Deployment & Verification Guide
**Project:** Campus Helpdesk Autonomous AI Robot  
**Confirmed Local Model:** `qwen2.5:3b` via Ollama  
**Embedding Engine:** `sentence-transformers/all-MiniLM-L6-v2`  
**Vector Store:** FAISS Index (IP / Cosine Similarity)  
**TTS Engine:** Piper (`en_US-lessac-medium`) / `pyttsx3`  
**STT Engine:** Faster-Whisper / SpeechRecognition  

---

## 1. System Requirements

- **Hardware:** Raspberry Pi 4 (4GB / 8GB) or Raspberry Pi 5 (4GB / 8GB).
- **OS:** Raspberry Pi OS (64-bit, Debian Bookworm recommended).
- **Storage:** Minimum 32 GB MicroSD or NVMe SSD (at least 10 GB free space).
- **Audio Hardware:** USB Microphone (or ReSpeaker HAT) and USB/3.5mm Speaker.

---

## 2. System Dependencies & OS Setup

Run the following on the Raspberry Pi terminal to install system-level audio, C++ build, and Python dependencies:

```bash
# Update package list and system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11/3.12, dev headers, Git, and audio libraries
sudo apt install -y python3-pip python3-venv python3-dev git \
                    portaudio19-dev libasound2-dev espeak-ng \
                    ffmpeg build-essential htop
```

---

## 3. Ollama Installation & Model Pulling

Install Ollama natively on ARM64 Linux and pull the confirmed Pi-safe model `qwen2.5:3b`:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Enable and start Ollama system service
sudo systemctl enable --now ollama

# Verify service status
systemctl status ollama

# Pull the confirmed, hallucination-resistant local model
ollama pull qwen2.5:3b

# Test local inference standalone
ollama run qwen2.5:3b "Who is the Chancellor of KLE Technological University?"
```

---

## 4. Repository & Environment Configuration

```bash
# Clone the repository
git clone https://github.com/YourRepo/campus-helpdesk.git
cd campus-helpdesk

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Create Production `.env` Config File:

Create `.env` in the project root (`/home/pi/campus-helpdesk/.env`):

```ini
APP_ENV=production
LOG_LEVEL=INFO

# Local LLM & Ollama Config
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OFFLINE_LLM_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT_SECONDS=180
OLLAMA_TEMPERATURE=0.0
OLLAMA_TOP_P=0.8
OLLAMA_TOP_K=40
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_CONTEXT_WINDOW=2048
OLLAMA_MAX_OUTPUT_TOKENS=512
OLLAMA_NUM_THREADS=4

# Disables Cloud Router for 100% Offline Mode on Pi
ENABLE_CLOUD_LLM_ROUTER=false

# RAG & Knowledge Base Paths
KNOWLEDGE_SOURCE_PATH=data/canonical_markdown
FAISS_INDEX_PATH=data/faiss
FAISS_ALLOW_DANGEROUS_DESERIALIZATION=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=16
EMBEDDING_NORMALIZE=true
EMBEDDING_LOCAL_FILES_ONLY=true

# Speech & Voice Settings
TTS_VOICE_MODEL=en_US-lessac-medium
TTS_PIPER_MODELS_DIR=data/piper
ALLOW_ONLINE_STT_FALLBACK=false
```

---

## 5. Knowledge Base & Asset Pre-caching

Run the following setup scripts once to build vector embeddings and pre-cache voices:

```bash
# 1. Build FAISS vector index from canonical markdown (already done — index is in data/faiss/)
#    Only needed if you add new knowledge documents:
python -m campus_helpdesk.ingest

# 2. Pre-cache ML models for offline use (REQUIRED before first offline run):
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', local_files_only=False)"
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', local_files_only=False)"

# 3. Install the campus-helpdesk package in editable mode:
pip install -e .

# 4. Pre-cache Piper TTS voice models (already in data/piper/ if transferred via USB)
python scripts/download_piper_voices.py
```

---

## 6. Hardware Verification Commands for Pi

Execute these exact commands on the Pi to verify system memory, pipeline accuracy, and voice hardware:

### 1. Verify Available Memory & Resource Usage
```bash
# Check available RAM (ensure at least 2.5 GB free for Ollama + Python process)
free -h

# Monitor CPU cores & RAM consumption live
htop
```

### 2. Verify Audio Microphones & Speakers
```bash
# List recording devices (Microphone index)
arecord -l

# List playback devices (Speaker index)
aplay -l

# Test microphone recording (5 seconds)
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 test_mic.wav

# Test speaker playback
aplay -D hw:1,0 test_mic.wav
```

### 3. Run Automated Pipeline Test Suite
```bash
# Execute unit & integration test suite
pytest tests/ -v
```

### 4. Run Multi-turn Voice Loop (Simulation Mode)
```bash
# Simulates full voice interaction cycle without requiring physical microphone
python scripts/voice_loop.py --simulate
```

### 5. Run Live Hardware Voice Loop
```bash
# Launches live voice interaction loop with physical mic and speaker
python scripts/voice_loop.py --mic-index 0 --speaker-index 0
```

### 6. Launch Production Runtimes
```bash
# Option A: Autonomous Robot CLI Runtime (Default systemd background service)
python -m campus_helpdesk.robot_main

# Option B: Web API & Kiosk UI Server at http://0.0.0.0:8000
python -m campus_helpdesk.main
```
