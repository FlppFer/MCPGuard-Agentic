import logging
from uuid import UUID

from app.models.schemas import AgenticAnalysisRequestDTO
from app.services import storage, analyzer, callback

logger = logging.getLogger(__name__)


async def execute(request: AgenticAnalysisRequestDTO) -> None:
    """Full analysis pipeline: download → analyze → callback.

    This runs as a background task so the /analyze endpoint can return 202 immediately.
    On any failure, we still attempt to call back with an empty findings array
    so the Go API can transition the analysis out of the waiting state.
    """
    analysis_id = str(request.analysis_id)
    extract_dir = None

    try:
        # 1. Download and extract source archive
        logger.info("Pipeline started for analysis_id=%s", analysis_id)
        extract_dir = await storage.download_and_extract(request.source_key)

        # 2. Collect supported source files
        all_files = storage.collect_source_files(extract_dir)
        if not all_files:
            logger.warning("No supported source files found for analysis_id=%s", analysis_id)

        # Filter to PR-changed files only when available
        if request.pr_changed_files:
            changed = set(request.pr_changed_files)
            logger.info(
                "PR changed files requested: %s",
                changed,
            )
            logger.debug("Available files sample: %s", list(all_files.keys())[:10])
            files = {p: c for p, c in all_files.items() if p in changed}
            missing = changed - set(files.keys())
            if missing:
                logger.warning(
                    "PR files not found in archive (path mismatch?): %s",
                    missing,
                )
            logger.info(
                "Filtered to %d PR-changed files (out of %d total) for analysis_id=%s",
                len(files), len(all_files), analysis_id,
            )
            if not files:
                logger.error(
                    "No PR files matched! Check path format. Requested: %s, Available sample: %s",
                    list(changed)[:5],
                    list(all_files.keys())[:5],
                )
        else:
            files = all_files

        # 3. Run LLM-based analysis
        logger.info(
            "Running analysis on %d files with %d static findings for analysis_id=%s",
            len(files), len(request.static_findings), analysis_id,
        )
        result = await analyzer.run_analysis(
            files=files,
            repo_url=request.repo_url,
            branch=request.branch,
            commit=request.commit,
            analysis_id=analysis_id,
            static_findings=request.static_findings,
        )

        # 4. Post findings to Go API
        await callback.post_findings(result)
        logger.info("Pipeline completed successfully for analysis_id=%s", analysis_id)

    except Exception as exc:
        logger.exception("Pipeline failed for analysis_id=%s: %s", analysis_id, exc)

        # Always call back so the Go API doesn't stay stuck
        try:
            from datetime import datetime, timezone
            from app.models.schemas import AgenticAnalysisResultDTO
            from app.config import settings

            error_result = AgenticAnalysisResultDTO(
                analysis_id=request.analysis_id,
                findings=[],
                summary=f"Analysis failed: {type(exc).__name__}: {exc}",
                model_used=settings.llm_model,
                timestamp=datetime.now(timezone.utc),
            )
            await callback.post_findings(error_result)
            logger.info("Error callback sent for analysis_id=%s", analysis_id)
        except Exception as cb_exc:
            logger.error(
                "Failed to send error callback for analysis_id=%s: %s",
                analysis_id, cb_exc,
            )

    finally:
        if extract_dir:
            storage.cleanup(extract_dir)
