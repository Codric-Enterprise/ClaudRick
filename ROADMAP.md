# ReVision — Roadmap

Roadmap for the core ReVision app (`src/revision/`). See `CLAUDE.md` for
architecture and conventions; this file only tracks direction.

## Done

- ✅ Per-client rate limiting and optional bearer auth on `/api/messages`.
- ✅ Docker image with `/healthz` HEALTHCHECK.
- ✅ CI: ruff (lint + format) and pytest on 3.11–3.13, plus a Docker build.

## Likely next steps toward production

- Streaming responses (SSE) for faster perceived latency.
- Persisting the model/config and per-tool token limits.
- Publishing the Docker image (registry) and a deploy target.
- A proper ASGI stack (e.g. FastAPI + uvicorn) *if* concurrency needs outgrow
  the stdlib `ThreadingHTTPServer` — this would add the first runtime deps.
- Shared/persistent rate-limit store (e.g. Redis) if run multi-process.
