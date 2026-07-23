# Phase 1 Architecture

## Scope

Phase 1 is a local, offline-first backend that runs on a laptop. It will expose
an HTTP API, retrieve approved campus knowledge locally, and produce responses
through a local Ollama-hosted Qwen 2.5 8B-class model.

## Dependency direction

`api -> application -> domain <- infrastructure`

The domain layer remains independent of FastAPI, LangChain, Ollama, FAISS, and
SQLite. Infrastructure implements domain-facing contracts; application use
cases compose those contracts.

## Intended data flow

`HTTP request -> API route -> application use case -> retrieval/LLM contracts -> local adapters -> response`

Persistent knowledge, vector indexes, model endpoints, and application
configuration will all stay local in Phase 1.
