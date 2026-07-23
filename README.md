# Offline-First Autonomous Campus Helpdesk Robot

Phase 1 provides a laptop-only backend foundation for a campus helpdesk robot.
It deliberately excludes voice, vision, hardware control, and robotics.

## Architecture

The project uses a layered, dependency-directed layout:

- `api`: FastAPI transport layer (routes, dependencies, request lifecycle).
- `application`: use cases and service orchestration.
- `domain`: business entities, policies, and repository contracts.
- `infrastructure`: adapters for Ollama, FAISS, SQLite, and external libraries.
- `shared`: cross-cutting utilities and common exceptions.

See `docs/module-roadmap.md` for the approval-gated implementation order.

## Status

Modules 1 through 3 are implemented: typed configuration, a modular FastAPI
application, local Ollama chat, and a reusable local RAG pipeline. The RAG
pipeline supports PDF loading, configurable chunking, Sentence Transformers
embeddings, FAISS persistence, and similarity search.

SQLite persistence, RAG-to-chat orchestration, voice, vision, and robotics
remain unimplemented.

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
