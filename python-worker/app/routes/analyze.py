import logging

from fastapi import APIRouter, BackgroundTasks, Response, status

from app.models.schemas import (
    AcceptedResponse,
    AgenticAnalysisRequestDTO,
    HealthResponse,
)
from app.services import pipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def analyze(request: AgenticAnalysisRequestDTO, background_tasks: BackgroundTasks):
    """Accept an analysis job and process it asynchronously."""
    logger.info(
        "Received analysis request: analysis_id=%s repo=%s branch=%s",
        request.analysis_id,
        request.repo_url,
        request.branch,
    )
    background_tasks.add_task(pipeline.execute, request)
    return AcceptedResponse(analysis_id=request.analysis_id)


@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse()
