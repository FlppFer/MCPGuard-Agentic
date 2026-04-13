import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging_config import setup_logging
from app.routes.analyze import router

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    from app.config import settings

    logger.info(
        "Worker starting — port=%s storage_mode=%s model=%s",
        settings.worker_port,
        settings.storage_mode,
        settings.llm_model,
    )
    yield
    logger.info("Worker shutting down")


app = FastAPI(
    title="MCPGuard Python Agentic Worker",
    version="1.0.0",
    description="AI-powered semantic security analysis for MCP tool repositories.",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.worker_port,
        log_level=settings.log_level.lower(),
    )
