# Offline-First Autonomous Campus Helpdesk Robot

An offline-first autonomous campus helpdesk robot powered by local LLM inference (Ollama), FAISS vector store retrieval, real-time speech recognition (Faster-Whisper), multi-lingual neural voice synthesis (Piper & Meta MMS-TTS), OpenCV camera presence detection, and automated Raspberry Pi systemd deployment.

## Architecture

The project features a dual execution entrypoint supported by a layered, dependency-directed core layout:

- **Autonomous Service Loop (`assistant_loop.py`)**: End-to-end voice and vision orchestration for Raspberry Pi deployment.
- `api`: FastAPI transport layer (routes, HTML web chat UI, dependencies, request lifecycle).
- `application`: use cases and service orchestration (`RAGChatService`, `RAGPipeline`).
- `domain`: business entities, policies, and repository contracts.
- `infrastructure`: adapters for Ollama, FAISS, Faster-Whisper, Meta MMS-TTS, OpenCV vision, and external libraries.
- `shared`: cross-cutting utilities and common exceptions.

See `docs/DEPLOYMENT.md` for complete Windows & Raspberry Pi installation guides.

## Status

Complete end-to-end implementation including:
- **Offline RAG & LLM**: Local Ollama model integration (`qwen2.5`) with FAISS vector similarity search and anti-hallucination prompting.
- **Multilingual Voice & Vision**: Faster-Whisper STT with candidate-list language detection (`en`, `hi`, `kn`), sub-second CPU TTS synthesis (Piper EN & Meta MMS-TTS HI/KN), and OpenCV camera person detection.
- **Web & Desktop Interfaces**: Glassmorphic HTML web chat interface (`http://localhost:8000/`) and PySide6 desktop GUI window (`demo.py`).
- **Raspberry Pi Deployment**: Automated systemd service installation and environment provisioning (`setup_pi_deployment.sh`, `campus-helpdesk-robot.service`).

## Run locally

Provision Python wheels, the Ollama model, and the Sentence Transformers model
from approved local media before deployment. Runtime requests are local only:

```powershell
ollama serve
```

Copy `.env.example` to `.env` and set `OLLAMA_MODEL` to the local Ollama tag
you provisioned. The code has no model-name default, so changing only this
environment value selects a future local model.

For the selected Qwen 2.5 8B-class deployment, use Ollama's published
`qwen2.5:7b` tag. If your offline registry provides another local Qwen tag,
set that tag in `.env` instead.

Then start the development server:

```powershell
uvicorn campus_helpdesk.main:app --app-dir src --reload
```

`POST /chat` returns `503 Service Unavailable` when Ollama is stopped or the
configured model cannot be used.

## Qwen 2.5 Inference

The sample environment uses conservative, helpdesk-oriented local settings:
temperature `0.2`, top-p `0.8`, top-k `40`, repeat penalty `1.1`, context
window `8192`, timeout `180` seconds, and a `512` token response limit. The
current JSON `/chat` endpoint is deliberately non-streaming; add a dedicated
streaming response endpoint before enabling token streaming.
