from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.db_models import ExtractorRow, ExtractionRunRow, RunStatus, RunTrigger
from app.services.extraction_service import run_extraction
from tests.conftest import EXTRACTOR_ID, NOW, RUN_ID

VALID_AGENT_DATA = {
    "shoes": [
        {
            "name": "Air Jordan 5",
            "category": "Men's Shoes",
            "price": 220,
        }
    ]
}

INVALID_AGENT_DATA = {
    "name": "Air Jordan 5",
    "category": "Men's Shoes",
    "price": 220,
}


def _build_finalized_run(updates: dict) -> ExtractionRunRow:
    completed_at = updates.get("completed_at")
    if isinstance(completed_at, str):
        completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

    return ExtractionRunRow(
        id=RUN_ID,
        extractor_id=EXTRACTOR_ID,
        status=RunStatus(updates["status"]),
        trigger=RunTrigger.MANUAL,
        started_at=NOW,
        completed_at=completed_at,
        duration_ms=updates.get("duration_ms"),
        data=updates.get("data"),
        validation_errors=updates.get("validation_errors", []),
        credits_used=updates.get("credits_used", 0),
        error=updates.get("error"),
    )


@pytest.mark.asyncio
async def test_run_extraction_completed_when_mocked_agent_matches_schema(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))

    with (
        patch(
            "app.services.extraction_service._get_extractor",
            return_value=sample_extractor,
        ),
        patch(
            "app.services.extraction_service.create_run",
            new=AsyncMock(return_value=running_run),
        ),
        patch(
            "app.services.extraction_service.finalize_run",
            finalize_mock,
        ),
        patch(
            "app.services.extraction_service._run_agent",
            return_value=(RunStatus.COMPLETED, VALID_AGENT_DATA, 5, None),
        ),
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.COMPLETED
    assert result.validation_errors == []
    assert result.error is None
    assert result.data == VALID_AGENT_DATA

    finalize_mock.assert_awaited_once()
    updates = finalize_mock.await_args.args[1]
    assert updates["status"] == RunStatus.COMPLETED.value
    assert updates["validation_errors"] == []


@pytest.mark.asyncio
async def test_run_extraction_failed_when_mocked_agent_does_not_match_schema(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))

    with (
        patch(
            "app.services.extraction_service._get_extractor",
            return_value=sample_extractor,
        ),
        patch(
            "app.services.extraction_service.create_run",
            new=AsyncMock(return_value=running_run),
        ),
        patch(
            "app.services.extraction_service.finalize_run",
            finalize_mock,
        ),
        patch(
            "app.services.extraction_service._run_agent",
            return_value=(RunStatus.COMPLETED, INVALID_AGENT_DATA, 5, None),
        ),
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.FAILED
    assert result.validation_errors
    assert any("shoes" in error for error in result.validation_errors)
    assert result.error is not None
    assert result.error.startswith("Schema validation failed")
    assert result.data == INVALID_AGENT_DATA

    finalize_mock.assert_awaited_once()
    updates = finalize_mock.await_args.args[1]
    assert updates["status"] == RunStatus.FAILED.value
    assert updates["validation_errors"] == result.validation_errors


@pytest.mark.asyncio
async def test_run_extraction_does_not_validate_when_agent_fails(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))

    with (
        patch(
            "app.services.extraction_service._get_extractor",
            return_value=sample_extractor,
        ),
        patch(
            "app.services.extraction_service.create_run",
            new=AsyncMock(return_value=running_run),
        ),
        patch(
            "app.services.extraction_service.finalize_run",
            finalize_mock,
        ),
        patch(
            "app.services.extraction_service._run_agent",
            return_value=(RunStatus.FAILED, None, 0, "Agent timed out"),
        ),
        patch(
            "app.services.extraction_service.validate_extraction",
        ) as validate_mock,
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.FAILED
    assert result.validation_errors == []
    assert result.error == "Agent timed out"
    validate_mock.assert_not_called()
