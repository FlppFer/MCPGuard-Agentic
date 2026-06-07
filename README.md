# MCPGuard Agentic

AI-powered agentic security analysis service for the [MCPGuard](https://github.com/FlppFer/MCPGuard) ecosystem.

This repository hosts the **Python agentic worker** that performs LLM-based
semantic analysis on MCP tool repositories. The [MCPGuard Go API](https://github.com/FlppFer/MCPGuard) enqueues
analysis jobs, uploads the source archive to S3, and dispatches them to this
worker, which downloads the archive, runs Google Gemini against the source,
and posts structured findings back to the Go API.

## Repository Layout

| Path | Description |
|------|-------------|
| [`python-worker/`](./python-worker) | FastAPI service implementing the agentic analysis pipeline. See its [README](./python-worker/README.md) for setup, configuration and API details. |
| [`python-agentic-worker-spec.md`](./python-agentic-worker-spec.md) | Functional and technical specification of the worker (contract with the Go API, threat taxonomy, pipeline stages). |
| [`CHANGELOG.md`](./CHANGELOG.md) | Version history (Keep a Changelog format). |
| [`LICENSE`](./LICENSE) | MIT license. |

## Quick Start

```bash
cd python-worker
cp .env.example .env          # fill in LLM_API_KEY (Google Gemini)
docker compose --profile worker up --build
```

The worker exposes:

- `POST /analyze` — submit an analysis job (called by the Go API).
- `GET  /health` — health check.

Default port: `5000`.

## How It Fits in MCPGuard

```
GitHub webhook ──► MCPGuard Go API ──► RabbitMQ ──► MCPGuard Go Worker
                                                          │
                                                          ▼
                                              S3 (source archive)
                                                          │
                                                          ▼
                                          MCPGuard Agentic (this repo)
                                                          │
                                                          ▼
                                              Findings ──► Go API callback
                                                          │
                                                          ▼
                                                  PR comment on GitHub
```

The agentic worker is **stateless** and always invokes the Go API callback —
even on failure — so the Go API can transition analyses out of the waiting
state.

## Documentation

- Worker setup, env vars, endpoints and architecture: [`python-worker/README.md`](./python-worker/README.md).
- Detailed contract and pipeline spec: [`python-agentic-worker-spec.md`](./python-agentic-worker-spec.md).
- Release notes: [`CHANGELOG.md`](./CHANGELOG.md).

## License

Licensed under the [MIT License](./LICENSE).
