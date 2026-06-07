# Changelog

All notable changes to the MCPGuard Python Agentic Worker will be documented in
this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Default Gemini model bumped from `gemini-3.0-flash` to `gemini-2.5-pro` in
  `app/config.py` and `.env.example`, aligning the worker with the model
  currently used in the integration test environment.
- README clarified that the worker is Gemini-only (no multi-provider
  abstraction) and documents the `MCPGUARD_CLIENT_ID` callback variable.

## [0.1.1] - 2026-06-07

### Added
- MIT `LICENSE` file at the repository root (`chore: add MIT license`,
  commit `7212df0`).

## [0.1.0] - 2026-04-12

### Added
- Initial release of the Python Agentic Worker
  (`Initial commit: Python Agentic Worker with Gemini LLM integration`,
  commit `6320807`).
- FastAPI service exposing `POST /analyze` and `GET /health`
  (`app/main.py`, `app/routes/analyze.py`).
- Gemini-based agentic analysis pipeline
  (`app/services/analyzer.py`, `app/services/pipeline.py`) calling the
  Google Gemini `generateContent` REST API.
- Storage abstraction supporting LocalStack/S3 and local filesystem
  (`app/services/storage.py`, `STORAGE_MODE=s3|local`).
- Callback client that posts findings back to the MCPGuard Go API
  (`app/services/callback.py`), including failure callbacks so the Go API
  can transition the analysis out of the waiting state.
- Pydantic request/response/finding schemas (`app/models/schemas.py`).
- Structured JSON logging configuration (`app/logging_config.py`).
- Configuration via `pydantic-settings` with environment variables defined
  in `.env.example` (`MCPGUARD_API_URL`, `MCPGUARD_API_KEY`,
  `MCPGUARD_CLIENT_ID`, `STORAGE_MODE`, `S3_*`, `AWS_*`, `LLM_API_KEY`,
  `LLM_MODEL`, `WORKER_PORT`, `LOG_LEVEL`).
- Containerization: multi-stage `Dockerfile` and `docker-compose.yaml`
  exposing the worker on port `5000`.
- Test suite under `tests/` covering analyzer, request models and the
  `/analyze` route (`test_analyze.py`, `test_analyzer.py`,
  `test_models.py`).
- Project specification document `python-agentic-worker-spec.md`.
- Repository-level `.gitignore` and VS Code launch configuration
  (`update gitignore`, commit `7e9a0ee`).

[Unreleased]: https://github.com/FlppFer/MCPGuard-Agentic/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/FlppFer/MCPGuard-Agentic/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/FlppFer/MCPGuard-Agentic/releases/tag/v0.1.0
