# MCPGuard — Python Agentic Worker

AI-powered semantic security analysis microservice for MCP tool repositories. Part of the MCPGuard ecosystem.

## Overview

This worker receives analysis jobs from the [MCPGuard Go API](https://github.com/FlppFer/MCPGuard), downloads source archives from S3, runs LLM-based security analysis, and posts structured findings back via a callback endpoint.

### Threat Categories Detected

- **Tool poisoning** — manipulated tool descriptions
- **Data exfiltration** — hidden data leaks in tool return values
- **Prompt injection** — embedded prompt manipulation in source/configs
- **Credential exposure** — hardcoded secrets or insecure credential patterns
- **Privilege escalation** — unauthorized capability expansion
- **Context manipulation** — agent context/memory tampering
- **Remote code execution** — arbitrary code execution via tool inputs
- **Supply chain risk** — suspicious dependencies, typosquatting

## Quick Start

### 1. Install dependencies

```bash
cd python-worker
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings (LLM API key, etc.)
```

### 3. Run locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

### 4. Run with Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze` | Submit an analysis job (returns `202 Accepted`) |
| `GET` | `/health` | Health check (`{"status": "ok"}`) |

### POST /analyze

```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "repo_url": "https://github.com/owner/repo.git",
  "branch": "main",
  "commit": "abc123def456",
  "source_key": "550e8400-e29b-41d4-a716-446655440000.zip"
}
```

## Configuration

See `.env.example` for all available environment variables. Key settings:

> The worker uses **Google Gemini** exclusively — the analysis call is made
> directly against the Gemini `generateContent` REST API. There is no
> multi-provider abstraction.

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | Google AI Studio API key (Gemini) |
| `LLM_MODEL` | No | Gemini model to use (default: `gemini-2.5-pro`) |
| `MCPGUARD_API_URL` | Yes | Go API base URL for callbacks |
| `MCPGUARD_API_KEY` | Yes | API key for authenticating with the Go API |
| `MCPGUARD_CLIENT_ID` | No | Client ID sent on callbacks (default: `dev-client`) |
| `STORAGE_MODE` | No | `s3` or `local` (default: `s3`) |

## Testing

```bash
pip install pytest pytest-asyncio anyio httpx
pytest -v
```

## Architecture

```
POST /analyze (from Go API)
  └─► Background Task
       ├─ 1. Download ZIP from S3 / local storage
       ├─ 2. Extract & collect supported source files
       ├─ 3. Send to LLM for security analysis
       └─ 4. POST findings to Go API callback
```

The worker always calls back — even on failure — so the Go API can transition the analysis out of the waiting state.