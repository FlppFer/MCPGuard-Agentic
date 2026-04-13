# MCPGuard — Python Agentic Worker: Functional & Technical Specification

> **Version**: 1.0
> **Date**: April 2026
> **Status**: Draft
> **Audience**: Python service developer

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Context](#2-architecture-context)
3. [Functional Requirements](#3-functional-requirements)
4. [Integration Points](#4-integration-points)
5. [API Contract — Inbound (Go → Python)](#5-api-contract--inbound-go--python)
6. [API Contract — Outbound (Python → Go)](#6-api-contract--outbound-python--go)
7. [Authentication](#7-authentication)
8. [Object Storage (S3)](#8-object-storage-s3)
9. [Data Models](#9-data-models)
10. [Analysis Pipeline Lifecycle](#10-analysis-pipeline-lifecycle)
11. [Error Handling](#11-error-handling)
12. [Configuration](#12-configuration)
13. [Docker / Deployment](#13-docker--deployment)
14. [Acceptance Criteria](#14-acceptance-criteria)

---

## 1. Overview

The **Python Agentic Worker** is an AI-powered semantic analysis microservice that complements MCPGuard's Go-based static analysis engine. It receives analysis jobs from the Go API, performs LLM-based security analysis on MCP tool source code, and reports findings back via a callback HTTP endpoint.

### What it does

- Receives analysis requests containing repository metadata and an S3 key for the source archive.
- Downloads the source archive from S3 (or local object storage).
- Runs LLM-based semantic analysis to detect security threats not caught by static rules.
- Posts structured findings back to the Go API's callback endpoint.

### What it does NOT do

- Does **not** manage analysis lifecycle (creation, status tracking, persistence) — the Go API owns that.
- Does **not** serve end-user HTTP traffic or webhooks.
- Does **not** clone git repositories — the Go API handles that and provides a pre-built ZIP archive.

---

## 2. Architecture Context

```
                        ┌──────────────┐
  GitHub Webhook ──────►│   Go API     │──── Static Analysis (built-in)
  Manual API Call ─────►│  :8080       │
                        │              │
                        │  POST /analyze ──────► ┌────────────────────┐
                        │  (submits job)         │  Python Worker     │
                        │              │◄──────  │  :5000             │
                        │  POST /v1/   │         │                    │
                        │  agentic_    │         │  1. Download ZIP   │
                        │  analysis    │         │  2. LLM Analysis   │
                        │  (callback)  │         │  3. POST findings  │
                        └──────────────┘         └────────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐         ┌────────────────────┐
                        │  PostgreSQL  │         │  S3 / LocalStack   │
                        │  (status DB) │         │  (source archives) │
                        └──────────────┘         └────────────────────┘
```

### Communication Flow

1. **Go API → Python Worker**: HTTP POST to `http://<worker_url>/analyze`
2. **Python Worker → S3**: Downloads source archive using the `source_key`
3. **Python Worker → Go API**: HTTP POST to `http://<go_api_url>/v1/agentic_analysis` (callback with findings)

---

## 3. Functional Requirements

### FR-1: Receive Analysis Job
The worker **MUST** expose a `POST /analyze` endpoint that accepts an `AgenticAnalysisRequestDTO` JSON body and responds with `202 Accepted` (or `200 OK`) to acknowledge receipt.

### FR-2: Download Source Archive
The worker **MUST** download the source ZIP from S3 using the `source_key` field from the request. The S3 key format is: `{analysis_id}.zip`.

### FR-3: Run LLM-Based Analysis
The worker **MUST** perform semantic analysis on the extracted source files. This includes but is not limited to:
- **Tool poisoning** — manipulated tool descriptions
- **Data exfiltration** — hidden data leaks in tool return values
- **Prompt injection** — embedded prompt manipulation in source/configs
- **Credential exposure** — hardcoded secrets or insecure credential patterns
- **Privilege escalation** — unauthorized capability expansion

### FR-4: Report Findings via Callback
After analysis completes, the worker **MUST** POST an `AgenticAnalysisResultDTO` to the Go API callback endpoint: `POST /v1/agentic_analysis`.

### FR-5: Health Check
The worker **SHOULD** expose a `GET /health` endpoint returning `{"status": "ok"}`.

---

## 4. Integration Points

| Direction | Protocol | From | To | Endpoint |
|-----------|----------|------|----|----------|
| **Inbound** | HTTP POST | Go API | Python Worker | `POST /analyze` |
| **Outbound** | HTTP POST | Python Worker | Go API | `POST /v1/agentic_analysis` |
| **Outbound** | S3 API | Python Worker | S3 / LocalStack | `GetObject` (`source_key`) |

---

## 5. API Contract — Inbound (Go → Python)

### `POST /analyze`

The Go API calls this endpoint to submit an analysis job.

#### Request Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `X-API-Key` | _(required in production — see [Authentication](#7-authentication))_ |
| `X-Client-ID` | _(required in production)_ |

#### Request Body — `AgenticAnalysisRequestDTO`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "repo_url": "https://github.com/owner/repo.git",
  "branch": "main",
  "commit": "abc123def456",
  "source_key": "550e8400-e29b-41d4-a716-446655440000.zip"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analysis_id` | `string` (UUID) | **Yes** | Unique identifier for this analysis run |
| `repo_url` | `string` | **Yes** | Git clone URL of the repository |
| `branch` | `string` | **Yes** | Branch name being analyzed |
| `commit` | `string` | **Yes** | Commit SHA being analyzed |
| `source_key` | `string` | **Yes** | S3 object key for the source ZIP archive |

#### Expected Responses

| Status | Meaning |
|--------|---------|
| `200 OK` or `202 Accepted` | Job acknowledged — analysis will proceed asynchronously |
| `400 Bad Request` | Invalid or missing fields |
| `500 Internal Server Error` | Worker-side failure |

> **Important**: The Go API has a **30-second HTTP timeout** for this call. The worker should acknowledge the request quickly and perform analysis asynchronously (e.g., in a background task/thread). Do **not** block the response until analysis completes.

---

## 6. API Contract — Outbound (Python → Go)

### `POST /v1/agentic_analysis` (Callback)

After analysis completes, the Python worker posts findings to this Go API endpoint.

#### Request Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `X-API-Key` | Value from `MCPGUARD_API_KEYS` env var |
| `X-Client-ID` | Client ID portion from `MCPGUARD_API_KEYS` |

#### Request Body — `AgenticAnalysisResultDTO`

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "findings": [
    {
      "category": "tool_poisoning",
      "description": "Tool description contains hidden instruction to redirect API calls to an external endpoint",
      "file_path": "src/tools/data_fetcher.py",
      "start_line": 15,
      "end_line": 22,
      "severity": "critical",
      "confidence": 0.92,
      "suggestion": "Remove hidden instructions from tool description. Use static descriptions only."
    },
    {
      "category": "credential_exposure",
      "description": "Hardcoded API key found in configuration handler",
      "file_path": "src/config.js",
      "start_line": 8,
      "end_line": 8,
      "severity": "high",
      "confidence": 0.85,
      "suggestion": "Move credential to environment variable or secret manager."
    }
  ],
  "summary": "Found 2 security issues: 1 critical tool poisoning, 1 high credential exposure.",
  "model_used": "gpt-4",
  "timestamp": "2026-04-05T14:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analysis_id` | `string` (UUID) | **Yes** | Must match the original request's `analysis_id` |
| `findings` | `AgenticFindingDTO[]` | **Yes** | Array of findings (can be empty `[]`) |
| `summary` | `string` | **Yes** | Human-readable summary of the analysis |
| `model_used` | `string` | No | LLM model identifier (e.g., `"gpt-4"`, `"claude-3"`) |
| `timestamp` | `string` (ISO 8601) | **Yes** | When the analysis completed |

#### `AgenticFindingDTO` Schema

| Field | Type | Required | Allowed Values |
|-------|------|----------|----------------|
| `category` | `string` | **Yes** | Free-form, recommended: `tool_poisoning`, `data_exfiltration`, `prompt_injection`, `credential_exposure`, `privilege_escalation`, `context_manipulation`, `remote_code_execution`, `supply_chain_risk` |
| `description` | `string` | **Yes** | Human-readable explanation of the finding |
| `file_path` | `string` | **Yes** | Relative path within the repository |
| `start_line` | `int` | No | 1-indexed line number where the issue starts |
| `end_line` | `int` | No | 1-indexed line number where the issue ends |
| `severity` | `string` | **Yes** | `"critical"`, `"high"`, `"medium"`, `"low"`, `"info"` |
| `confidence` | `float` | **Yes** | `0.0` to `1.0` — LLM confidence in the finding |
| `suggestion` | `string` | **Yes** | Recommended mitigation/fix |

#### Expected Responses from Go API

| Status | Meaning | Action |
|--------|---------|--------|
| `200 OK` | Result received and persisted | `{"status": "received"}` |
| `400 Bad Request` | Missing `analysis_id` or malformed body | Log and retry or discard |
| `404 Not Found` | `analysis_id` not found in DB | Log error — analysis may have been deleted |
| `500 Internal Server Error` | Go API internal failure | Retry with exponential backoff |

---

## 7. Authentication

The Go API protects all `/v1/*` endpoints (except webhooks) with **API key authentication**.

### Headers Required

| Header | Description |
|--------|-------------|
| `X-API-Key` | The API key value |
| `X-Client-ID` | The client identifier |

### How Keys Are Configured

The Go API reads API keys from the environment variable specified in `auth.api_keys_key` (default: `MCPGUARD_API_KEYS`).

**Format**: `client_id:api_key,client_id2:api_key2`

**Example**:
```bash
MCPGUARD_API_KEYS="python-worker:sk-worker-secret-key-123"
```

The Python worker must send:
```
X-Client-ID: python-worker
X-API-Key: sk-worker-secret-key-123
```

> **Local development**: The default compose value is `dev-client:dev-key`.

---

## 8. Object Storage (S3)

### Source Archive Download

| Property | Value |
|----------|-------|
| **Bucket** | `mcpguard-artifacts` (production) |
| **Key pattern** | `{analysis_id}.zip` |
| **Format** | ZIP archive containing the full repository checkout |
| **Content** | All supported files: `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.md` |

### Local Development (Mock Storage)

When `object_storage.mock: true`, files are stored on the local filesystem under `mcpguard-local-storage/`. The Python worker should support both:
- **Real S3** (production): Use `boto3` with standard AWS credentials
- **LocalStack** (development): Use `boto3` with endpoint `http://localstack:4566`
- **Local filesystem** (simple dev): Read directly from the shared Docker volume at `/app/mcpguard-local-storage/`

### S3 Key Constants (from Go API)

```
Source archive:    "{analysis_id}.zip"
Static result:     "analysis-results/{analysis_id}_static.json"
Agentic result:    "analysis-results/{analysis_id}_agentic.json"
```

> The Python worker only needs to **read** the source archive. It does **not** upload results to S3 — results are posted via the HTTP callback, and the Go API handles persistence.

---

## 9. Data Models

### Static Analysis Finding (from Go API — for reference)

The static analysis engine produces findings in this format. The Python worker's findings are displayed alongside these in the merged result view.

```json
{
  "rule_id": "MCP-JS-CMD-001",
  "message": "Dangerous exec() call with user input",
  "file_path": "src/handler.js",
  "line": 42,
  "severity": "critical",
  "snippet": "exec(userInput)"
}
```

### Merged Result (returned by `GET /v1/analysis/{id}/result/full`)

```json
{
  "analysis_id": "...",
  "status": "completed",
  "static_result": {
    "analysis_id": "...",
    "files_analyzed": 12,
    "findings": [ /* static findings */ ]
  },
  "agentic_result": {
    "analysis_id": "...",
    "findings": [ /* agentic findings */ ],
    "summary": "...",
    "model_used": "gpt-4",
    "timestamp": "..."
  }
}
```

---

## 10. Analysis Pipeline Lifecycle

The Go API tracks analysis status through the following states. The Python worker's role spans states **7 → 10**.

| # | Status | Owner | Description |
|---|--------|-------|-------------|
| 1 | `created` | Go API | Analysis entity created in DB |
| 2 | `queued` | Go API | Published to message queue (if enabled) |
| 3 | `downloading_repo` | Go API | Git clone in progress |
| 4 | `uploading_source` | Go API | ZIP uploaded to S3 |
| 5 | `static_analysis_running` | Go API | Static rules executing |
| 6 | `static_analysis_done` | Go API | Static analysis complete |
| **7** | **`waiting_agent_analysis`** | **Go API** | **Job submitted to Python worker** |
| **8** | **`agent_analysis_running`** | **Python Worker** | **LLM analysis in progress** (informational — Go API sets this on submission) |
| **9** | **`agent_analysis_done`** | **Go API** | **Agentic result received via callback** |
| **10** | **`completed`** | **Go API** | **Both analyses finished** |
| — | `failed` | Either | Error at any stage |

### Sequence Diagram

```
Go API                          Python Worker                    S3
  │                                  │                            │
  │──POST /analyze──────────────────►│                            │
  │◄─────────202 Accepted───────────│                            │
  │                                  │                            │
  │                                  │──GetObject(source_key)────►│
  │                                  │◄─────────ZIP data──────────│
  │                                  │                            │
  │                                  │  [extract + LLM analysis]  │
  │                                  │                            │
  │◄──POST /v1/agentic_analysis─────│                            │
  │──────────200 OK─────────────────►│                            │
  │                                  │                            │
  │  [Go API persists to S3,         │                            │
  │   updates status → completed]    │                            │
```

---

## 11. Error Handling

### Worker Failures

If the Python worker fails to analyze, it should still call back with an empty findings array and an error summary:

```json
{
  "analysis_id": "...",
  "findings": [],
  "summary": "Analysis failed: LLM API rate limit exceeded",
  "model_used": "gpt-4",
  "timestamp": "2026-04-05T14:30:00Z"
}
```

This allows the Go API to transition the analysis to `completed` rather than leaving it stuck in `waiting_agent_analysis`.

### Retry Strategy

- If the callback to `POST /v1/agentic_analysis` fails, the worker **SHOULD** retry up to 3 times with exponential backoff (1s, 5s, 15s).
- If all retries fail, log the error and discard — the Go API will eventually time out the analysis.

### Go API Timeout

- The Go API HTTP client has a **30-second timeout** when calling `POST /analyze`.
- The worker **MUST** respond within 30 seconds — acknowledge quickly and process asynchronously.

---

## 12. Configuration

### Environment Variables (Python Worker)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCPGUARD_API_URL` | **Yes** | `http://mcpguard-api:8080` | Base URL of the Go API for callbacks |
| `MCPGUARD_API_KEY` | **Yes** | — | API key for authenticating with Go API |
| `MCPGUARD_CLIENT_ID` | **Yes** | — | Client ID for authenticating with Go API |
| `AWS_ACCESS_KEY_ID` | Prod | — | S3 credentials |
| `AWS_SECRET_ACCESS_KEY` | Prod | — | S3 credentials |
| `AWS_REGION` | Prod | `us-east-1` | S3 region |
| `S3_BUCKET` | Prod | `mcpguard-artifacts` | S3 bucket name |
| `S3_ENDPOINT` | Dev | `http://localstack:4566` | For LocalStack |
| `STORAGE_MODE` | No | `s3` | `s3` or `local` — when `local`, read from `/app/mcpguard-local-storage/` |
| `LLM_PROVIDER` | **Yes** | — | `openai`, `anthropic`, `azure`, etc. |
| `LLM_API_KEY` | **Yes** | — | API key for the LLM provider |
| `LLM_MODEL` | No | `gpt-4` | Model to use for analysis |
| `WORKER_PORT` | No | `5000` | Port the worker listens on |
| `LOG_LEVEL` | No | `info` | Logging level |

---

## 13. Docker / Deployment

### Docker Compose Service Definition

Add the Python worker to the existing `docker-compose.yaml`:

```yaml
  python-worker:
    build:
      context: ./python-worker
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - MCPGUARD_API_URL=http://mcpguard-api:8080
      - MCPGUARD_API_KEY=dev-key
      - MCPGUARD_CLIENT_ID=dev-client
      - STORAGE_MODE=local
      - LLM_PROVIDER=openai
      - LLM_API_KEY=${OPENAI_API_KEY}
      - LLM_MODEL=gpt-4
    volumes:
      - mcpguard-storage:/app/mcpguard-local-storage
    depends_on:
      - mcpguard-api
    restart: unless-stopped
```

### Key Points

- Shares the `mcpguard-storage` volume so it can read source archives when `STORAGE_MODE=local`.
- In production (`config/prod.yaml`), the Go API expects the worker at `http://python-worker:5000`.
- The worker only needs network access to the Go API and S3 — no database access required.

### Recommended Tech Stack

| Component | Suggestion |
|-----------|------------|
| **Framework** | FastAPI (async) or Flask |
| **HTTP client** | `httpx` (async) or `requests` |
| **S3 client** | `boto3` |
| **LLM client** | `openai`, `anthropic`, or `litellm` for multi-provider |
| **Task runner** | `asyncio` background tasks (FastAPI), `threading`, or Celery |
| **Container** | Python 3.11+ slim image |

---

## 14. Acceptance Criteria

### Must Have

- [ ] `POST /analyze` endpoint accepts `AgenticAnalysisRequestDTO` and returns `202` within 5 seconds
- [ ] Downloads source archive from S3 (or local volume) using `source_key`
- [ ] Extracts ZIP and runs LLM-based security analysis
- [ ] Posts `AgenticAnalysisResultDTO` to `POST /v1/agentic_analysis` with correct auth headers
- [ ] `analysis_id` in the callback matches the original request
- [ ] Findings include all required fields: `category`, `description`, `file_path`, `severity`, `confidence`, `suggestion`
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] Handles errors gracefully — always calls back, even with empty findings

### Should Have

- [ ] Retry logic (3 attempts, exponential backoff) for callback failures
- [ ] Configurable LLM provider/model via environment variables
- [ ] Structured JSON logging
- [ ] Dockerfile with multi-stage build
- [ ] Rate limiting awareness for LLM API calls

### Nice to Have

- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Support for multiple LLM providers via `litellm`
- [ ] Caching of analysis results for identical source archives
- [ ] Configurable analysis depth/scope

---

## Appendix: Quick Reference

### Go API Endpoints the Python Worker Interacts With

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `POST` | `/v1/agentic_analysis` | `X-API-Key` + `X-Client-ID` | Submit analysis findings (callback) |
| `GET` | `/health` | None | Verify Go API is reachable |

### Go API Config (for reference)

```yaml
# config/default.yaml
agentic:
  enabled: true
  mock: true                        # Set to false to use real Python worker
  worker_url: "http://localhost:5000"

# config/prod.yaml
agentic:
  enabled: true
  mock: false
  worker_url: "http://python-worker:5000"
```

When `mock: true`, the Go API uses a built-in mock that generates fake agentic findings. Set `mock: false` to route to the real Python worker.
