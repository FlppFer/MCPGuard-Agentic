import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from app.services.analyzer import run_analysis, _parse_llm_response


def _gemini_response(findings: list, summary: str) -> dict:
    """Build a fake Gemini generateContent response."""
    return {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {"text": json.dumps({"findings": findings, "summary": summary})}
                    ],
                }
            }
        ],
    }


def test_parse_llm_response_valid_json():
    raw = json.dumps({
        "findings": [
            {
                "category": "credential_exposure",
                "description": "Hardcoded key",
                "file_path": "config.py",
                "start_line": 10,
                "end_line": 10,
                "severity": "high",
                "confidence": 0.88,
                "suggestion": "Use env vars",
            }
        ],
        "summary": "Found 1 issue.",
    })
    findings, summary = _parse_llm_response(raw)
    assert len(findings) == 1
    assert findings[0].category == "credential_exposure"
    assert summary == "Found 1 issue."


def test_parse_llm_response_empty_findings():
    raw = json.dumps({"findings": [], "summary": "Clean."})
    findings, summary = _parse_llm_response(raw)
    assert findings == []
    assert summary == "Clean."


def test_parse_llm_response_markdown_wrapped():
    inner = json.dumps({"findings": [], "summary": "No issues."})
    raw = f"```json\n{inner}\n```"
    findings, summary = _parse_llm_response(raw)
    assert findings == []
    assert summary == "No issues."


def test_parse_llm_response_invalid():
    findings, summary = _parse_llm_response("this is not json at all")
    assert findings == []
    assert "unparseable" in summary.lower()


def test_parse_llm_response_malformed_finding():
    raw = json.dumps({
        "findings": [
            {"category": "test"},  # missing required fields
            {
                "category": "valid",
                "description": "ok",
                "file_path": "a.py",
                "severity": "low",
                "confidence": 0.5,
                "suggestion": "none",
            },
        ],
        "summary": "Partial.",
    })
    findings, summary = _parse_llm_response(raw)
    assert len(findings) == 1
    assert findings[0].category == "valid"


@pytest.mark.anyio
async def test_run_analysis_calls_gemini():
    fake_resp = httpx.Response(200, json=_gemini_response([], "All clear."))

    with patch("app.services.analyzer.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=fake_resp)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await run_analysis(
            files={"test.py": "print('hello')"},
            repo_url="https://github.com/o/r.git",
            branch="main",
            commit="abc",
            analysis_id=str(uuid4()),
        )

    assert "no security issues found" in result.summary.lower()
    assert result.findings == []
    assert result.model_used is not None
    instance.post.assert_called_once()


@pytest.mark.anyio
async def test_run_analysis_multiple_files():
    """Verify one Gemini call is made per file."""
    fake_resp = httpx.Response(200, json=_gemini_response([], "Clean."))

    with patch("app.services.analyzer.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post = AsyncMock(return_value=fake_resp)
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        files = {
            "src/a.py": "print('a')",
            "src/b.js": "console.log('b')",
            "config.yaml": "key: value",
        }

        result = await run_analysis(
            files=files,
            repo_url="https://github.com/o/r.git",
            branch="main",
            commit="abc",
            analysis_id=str(uuid4()),
        )

    assert instance.post.call_count == 3
    assert result.findings == []
