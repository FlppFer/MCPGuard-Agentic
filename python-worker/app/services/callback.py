import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config import settings
from app.models.schemas import AgenticAnalysisResultDTO

logger = logging.getLogger(__name__)

CALLBACK_PATH = "/v1/agentic_analysis"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def post_findings(result: AgenticAnalysisResultDTO) -> None:
    """POST analysis findings to the Go API callback endpoint with retry."""
    url = f"{settings.mcpguard_api_url.rstrip('/')}{CALLBACK_PATH}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": settings.mcpguard_api_key,
        "X-Client-ID": settings.mcpguard_client_id,
    }
    payload = result.model_dump(mode="json")

    logger.info(
        "Posting findings for analysis_id=%s to %s (%d findings)",
        result.analysis_id,
        url,
        len(result.findings),
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

    logger.info("Callback succeeded for analysis_id=%s — status %s", result.analysis_id, resp.status_code)
