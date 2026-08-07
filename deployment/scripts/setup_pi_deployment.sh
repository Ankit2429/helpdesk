#!/usr/bin/env bash
# ==============================================================================
# setup_pi_deployment.sh
# End-to-End Automated Deployment Script for Raspberry Pi OS (Linux ARM64)
# ==============================================================================

set -euo pipefail

echo "======================================================================="
echo "   STARTING CAMPUS HELPDESK ROBOT RASPBERRY PI DEPLOYMENT SETUP"
echo "======================================================================="

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REAL_USER="${SUDO_USER:-$USER}"

echo "Deployment Target Directory : $APP_DIR"
echo "Deployment Target User      : $REAL_USER"

# 1. Ensure System Packages & Build Tools are Installed
echo -e "\n[1/7] Installing APT System Dependencies & Build Tools..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    g++ \
    python3-dev \
    python3-venv \
    python3-pip \
    ffmpeg \
    espeak-ng \
    portaudio19-dev \
    libopenblas-dev \
    libatlas-base-dev \
    v4l-utils \
    curl \
    git \
    tar

# 2. Check and Install Ollama for local LLM execution
echo -e "\n[2/7] Verifying Ollama Installation..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing Ollama for Linux ARM64..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

echo "Ensuring Ollama server is active and pulling qwen2.5:3b model..."
sudo systemctl enable --now ollama || true
ollama pull qwen2.5:3b

# 3. Create Python Virtual Environment
echo -e "\n[3/7] Setting up Python Virtual Environment (.venv)..."
cd "$APP_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip setuptools wheel

# 4. Install Python Requirements & Handle Piper ARM64 Wheel Build Fallback
echo -e "\n[4/7] Installing Python Package Dependencies..."
if ! pip install -r requirements.txt; then
    echo "WARNING: pip install requirements.txt failed. Retrying with Piper ARM64 binary fallback..."
    # If piper-tts wheel build fails on ARM64, install requirements without piper-tts and fetch standalone Piper ARM64 binary
    grep -v "^piper-tts" requirements.txt > req_no_piper.txt
    pip install -r req_no_piper.txt
    rm -f req_no_piper.txt

    # Download prebuilt standalone Piper Linux ARM64 binary from rhasspy/piper GitHub releases
    echo "Downloading official Piper Linux ARM64 binary release..."
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
    mkdir -p bin/piper_bin
    curl -L "$PIPER_URL" | tar -xz -C bin/piper_bin --strip-components=1
    chmod +x bin/piper_bin/piper
    echo "Standalone Piper ARM64 binary installed at: $APP_DIR/bin/piper_bin/piper"
fi

echo "Installing local campus-helpdesk package in editable mode..."
pip install -e .

# 5. Pre-render Canned Indic TTS Cache
echo -e "\n[5/7] Pre-rendering Indic Canned FAQ WAV Audio Cache..."
python scripts/precache_tts.py || true

# 6. Dynamically Patch systemd Service Paths
echo -e "\n[6/7] Dynamically Patching systemd Service Working Directory & Executable..."
SERVICE_SRC="$APP_DIR/deployment/systemd/campus-helpdesk-robot.service"
SERVICE_TMP="/tmp/campus-helpdesk-robot.service"

if [ -f "$SERVICE_SRC" ]; then
    cp "$SERVICE_SRC" "$SERVICE_TMP"
    # Replace default placeholder path /home/pi/campus-helpdesk with actual $APP_DIR
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$APP_DIR|g" "$SERVICE_TMP"
    sed -i "s|ExecStart=.*|ExecStart=$APP_DIR/.venv/bin/python -m campus_helpdesk.robot_main|g" "$SERVICE_TMP"
    sed -i "s|EnvironmentFile=-.*|EnvironmentFile=-$APP_DIR/.env|g" "$SERVICE_TMP"
    sed -i "s|User=.*|User=$REAL_USER|g" "$SERVICE_TMP"
    # Patch PYTHONPATH and HOME to correct actual app directory
    sed -i "s|Environment=PYTHONPATH=.*|Environment=PYTHONPATH=$APP_DIR/src|g" "$SERVICE_TMP"
    sed -i "s|Environment=HOME=.*|Environment=HOME=/home/$REAL_USER|g" "$SERVICE_TMP"

    echo "Patched service unit file:"
    grep -E "(User|WorkingDirectory|ExecStart|PYTHONPATH)" "$SERVICE_TMP"

    sudo cp "$SERVICE_TMP" /etc/systemd/system/campus-helpdesk-robot.service
    rm -f "$SERVICE_TMP"
    sudo systemctl daemon-reload
    sudo systemctl enable campus-helpdesk-robot.service
    echo "Service registered and enabled!"
else
    echo "WARNING: $SERVICE_SRC not found in $APP_DIR."
fi

# 7. Pre-download ML Models for Offline Use
echo -e "\n[7/7] Pre-caching HuggingFace ML Models for Offline Operation..."
source "$APP_DIR/.venv/bin/activate"
python -c "
from sentence_transformers import SentenceTransformer
print('Downloading sentence-transformers/all-MiniLM-L6-v2...')
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', local_files_only=False)
print('Embedding model cached.')
" || echo "WARNING: Embedding model download failed. Ensure internet is available or pre-cache manually."

python -c "
from sentence_transformers import CrossEncoder
print('Downloading cross-encoder/ms-marco-MiniLM-L-6-v2...')
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', local_files_only=False)
print('Reranker model cached.')
" || echo "WARNING: Reranker model download failed. Ensure internet is available or pre-cache manually."

# Final Instructions
echo -e "\n======================================================================="
echo "   DEPLOYMENT SETUP COMPLETE! READY FOR PHYSICAL HARDWARE EXECUTION"
echo "======================================================================="
echo ""
echo "QUICK VERIFICATION:"
echo "  1. Test Ollama:     ollama run qwen2.5:3b 'Who is the Chancellor of KLE Tech?'"
echo "  2. Test RAG import: $APP_DIR/.venv/bin/python -c 'from campus_helpdesk.main import app; print(\"Import OK\")'"
echo "  3. Run test suite:  cd $APP_DIR && $APP_DIR/.venv/bin/python -m pytest tests/ -q"
echo "  4. Start service:   sudo systemctl start campus-helpdesk-robot"
echo "  5. View live logs:  journalctl -u campus-helpdesk-robot -f"
echo ""
echo "Robot Runtime (foreground): python -m campus_helpdesk.robot_main --mock"
echo "Web API Server:             uvicorn campus_helpdesk.main:app --app-dir $APP_DIR/src --host 0.0.0.0 --port 8000"
