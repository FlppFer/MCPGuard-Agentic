# MCPGuard Agentic

AI-powered agentic security analysis service for the [MCPGuard](https://github.com/FlppFer/MCPGuard) ecosystem.

This repository hosts the **Python agentic worker** that performs LLM-based
semantic analysis on MCP tool repositories. The [MCPGuard Go API](https://github.com/FlppFer/MCPGuard) enqueues
analysis jobs, uploads the source archive to S3, and dispatches them to this
worker, which downloads the archive, runs Google Gemini against the source,
and posts structured findings back to the Go API.

## What It Does

- Receives analysis jobs from the Go API over HTTP (`POST /analyze`).
- Downloads the source archive from S3 (or LocalStack in development) using the `source_key` provided by the Go API.
- Extracts the archive and collects supported source files (Python, JavaScript/TypeScript, JSON, YAML, etc.).
- Sends the source to **Google Gemini** (`generateContent` REST API) with a security-focused prompt covering tool poisoning, prompt injection, credential exposure, privilege escalation, RCE and supply-chain risk.
- Posts the resulting findings back to the Go API callback (`POST /v1/agentic_analysis`) — even on failure, so the Go API can transition the analysis out of the waiting state.

## How It Works

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

The worker is **stateless**: it owns no database and no analysis lifecycle. The Go API is the source of truth for analyses, and this service is invoked per job.

## Run Locally

Prerequisites: Docker + a Google Gemini API key from <https://aistudio.google.com/apikey>.

```bash
cd python-worker
cp .env.example .env
# edit .env and set LLM_API_KEY=<your-gemini-key>
docker compose --profile worker up --build
```

The worker will be available at `http://localhost:5000`:

- `POST /analyze` — submit an analysis job (called by the Go API).
- `GET  /health` — health check (`{"status": "ok"}`).

For a full local stack (Go API + Postgres + RabbitMQ + LocalStack + this worker), follow the instructions in the [MCPGuard Go API repository](https://github.com/FlppFer/MCPGuard) and bring up its `docker-compose.yaml` with the `--profile all` flag, then start this worker in a separate `docker compose --profile worker up`.

### Run without Docker

```bash
cd python-worker
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

## Configuration

Key environment variables (see [`python-worker/.env.example`](./python-worker/.env.example) for the full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | Google AI Studio API key (Gemini). |
| `LLM_MODEL` | No | Gemini model (default: `gemini-2.5-pro`). |
| `MCPGUARD_API_URL` | Yes | Go API base URL for the findings callback. |
| `MCPGUARD_API_KEY` | Yes | API key used to authenticate against the Go API. |
| `MCPGUARD_CLIENT_ID` | No | Client ID sent on callbacks (default: `dev-client`). |
| `STORAGE_MODE` | No | `s3` or `local` (default: `s3`). |
| `S3_ENDPOINT` / `S3_BUCKET` | When `STORAGE_MODE=s3` | LocalStack or AWS S3 endpoint and bucket. |

## Further Reading

- Detailed worker docs (endpoints, payload schemas, testing): [`python-worker/README.md`](./python-worker/README.md).
- Functional and technical specification (contract with the Go API, threat taxonomy, pipeline stages): [`python-agentic-worker-spec.md`](./python-agentic-worker-spec.md).
- Release notes: [`CHANGELOG.md`](./CHANGELOG.md).
