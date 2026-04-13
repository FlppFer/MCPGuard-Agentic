from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AgenticAnalysisRequestDTO,
    AgenticAnalysisResultDTO,
    AgenticFindingDTO,
    Severity,
)


def test_request_dto_valid():
    dto = AgenticAnalysisRequestDTO(
        analysis_id=uuid4(),
        repo_url="https://github.com/owner/repo.git",
        branch="main",
        commit="abc123",
        source_key="test.zip",
    )
    assert dto.branch == "main"


def test_request_dto_missing_field():
    with pytest.raises(ValidationError):
        AgenticAnalysisRequestDTO(
            repo_url="https://github.com/owner/repo.git",
            branch="main",
            commit="abc123",
            source_key="test.zip",
        )


def test_finding_dto_valid():
    f = AgenticFindingDTO(
        category="tool_poisoning",
        description="Bad tool description",
        file_path="src/tool.py",
        start_line=1,
        end_line=5,
        severity=Severity.critical,
        confidence=0.9,
        suggestion="Fix it",
    )
    assert f.severity == Severity.critical
    assert f.confidence == 0.9


def test_finding_dto_confidence_out_of_range():
    with pytest.raises(ValidationError):
        AgenticFindingDTO(
            category="tool_poisoning",
            description="test",
            file_path="a.py",
            severity="high",
            confidence=1.5,
            suggestion="fix",
        )


def test_result_dto_valid():
    aid = uuid4()
    r = AgenticAnalysisResultDTO(
        analysis_id=aid,
        findings=[],
        summary="No issues found.",
        model_used="gpt-4",
        timestamp=datetime.now(timezone.utc),
    )
    assert r.analysis_id == aid
    assert r.findings == []


def test_finding_severity_values():
    for sev in ["critical", "high", "medium", "low", "info"]:
        f = AgenticFindingDTO(
            category="test",
            description="test",
            file_path="a.py",
            severity=sev,
            confidence=0.5,
            suggestion="fix",
        )
        assert f.severity.value == sev
