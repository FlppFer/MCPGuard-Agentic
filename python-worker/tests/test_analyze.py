import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def analysis_request():
    aid = str(uuid4())
    return {
        "analysis_id": aid,
        "repo_url": "https://github.com/owner/repo.git",
        "branch": "main",
        "commit": "abc123def456",
        "source_key": f"{aid}.zip",
    }


@pytest.mark.anyio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_analyze_returns_202(analysis_request):
    with patch("app.routes.analyze.pipeline") as mock_pipeline:
        mock_pipeline.execute = AsyncMock()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/analyze", json=analysis_request)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["analysis_id"] == analysis_request["analysis_id"]


@pytest.mark.anyio
async def test_analyze_rejects_missing_fields():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/analyze", json={"repo_url": "x"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_analyze_rejects_invalid_uuid():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/analyze",
            json={
                "analysis_id": "not-a-uuid",
                "repo_url": "https://github.com/o/r.git",
                "branch": "main",
                "commit": "abc",
                "source_key": "bad.zip",
            },
        )
    assert resp.status_code == 422
