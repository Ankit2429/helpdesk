# Offline AI Model Provisioning & Setup Guide

## 1. Local Language Model (Ollama & Qwen 2.5 7B)

The application uses Ollama to host the quantized **Qwen 2.5 7B** language model (`qwen2.5:7b`).

### Setup Commands
```powershell
# Install model tag into local Ollama registry
ollama pull qwen2.5:7b

# Verify installed models
ollama list
```

### Environment Configuration (`.env`)
```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=180.0
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.8
OLLAMA_TOP_K=40
OLLAMA_REPEAT_PENALTY=1.1
OLLAMA_CONTEXT_WINDOW=8192
OLLAMA_MAX_OUTPUT_TOKENS=512
```

---

## 2. Sentence Transformers Embeddings Model

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Mode**: Offline vector embedding generation for FAISS store.

```ini
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
EMBEDDING_NORMALIZE=true
```

---

## 3. Faster-Whisper Speech Recognition (STT)

- **Model**: Faster-Whisper `base`
- **Device**: CPU (Int8 quantization for lightweight offline execution)

```ini
WHISPER_MODEL_SIZE=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

---

## 4. Text-to-Speech (TTS) Voice Engine

- **Engine**: Piper (offline neural TTS, ONNX runtime). Falls back to
  PyTTSx3 (SAPI5 / SpeechDispatcher) automatically if the Piper model
  files below are not found.
- **Voice Model**: `en_US-lessac-medium`

Download the voice model + config into `data/piper/` (filenames must match
`TTS_VOICE_MODEL` exactly):

```powershell
mkdir data\piper
curl -L -o data\piper\en_US-lessac-medium.onnx ^
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -o data\piper\en_US-lessac-medium.onnx.json ^
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

```ini
TTS_VOICE_MODEL=en_US-lessac-medium
TTS_PIPER_MODELS_DIR=data/piper
TTS_USE_CUDA=false
```
