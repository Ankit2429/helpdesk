# Approval-Gated Module Roadmap

No module below is implemented until you approve it explicitly.

1. **Core configuration and observability** — typed settings, logging, error model, and application factory.
2. **Domain model** — campus knowledge entities, repository contracts, and response policies.
3. **SQLite persistence** — schema, migrations approach, repositories, and local document storage.
4. **Knowledge ingestion** — document validation, chunking, embeddings, and FAISS indexing.
5. **Local AI adapters** — Ollama/Qwen 2.5 and LangChain integration behind domain contracts.
6. **Helpdesk application service** — retrieval-augmented answer orchestration and guardrails.
7. **FastAPI interface** — health and helpdesk endpoints, schemas, dependency wiring, and error handling.
8. **Quality and operations** — tests, local run guidance, observability checks, and packaging hardening.

Voice, vision, robot hardware, navigation, and actuator integrations are outside
the Phase 1 scope and have no directories or dependencies in this scaffold.
