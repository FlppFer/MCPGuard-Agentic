from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Inbound DTO (Go API → Python Worker) ────────────────────────────────────


class StaticFindingContext(BaseModel):
    rule_id: str
    file_path: str
    line: int
    severity: str
    message: str


class AgenticAnalysisRequestDTO(BaseModel):
    analysis_id: UUID
    repo_url: str
    branch: str
    commit: str
    source_key: str
    pr_changed_files: list[str] = []
    static_findings: list[StaticFindingContext] = []


# ── Outbound DTOs (Python Worker → Go API) ──────────────────────────────────


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class AgenticFindingDTO(BaseModel):
    category: str
    description: str
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    suggestion: str


class AgenticAnalysisResultDTO(BaseModel):
    analysis_id: UUID
    findings: list[AgenticFindingDTO]
    summary: str
    model_used: Optional[str] = None
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def default_timestamp(cls, v: datetime | None) -> datetime:
        return v or datetime.utcnow()


# ── Simple response models ──────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"


class AcceptedResponse(BaseModel):
    status: str = "accepted"
    analysis_id: UUID
