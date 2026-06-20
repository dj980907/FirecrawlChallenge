from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.db_models import (
    ExtractorRow,
    ExtractionRunRow,
    RepairStrategy,
    RunStatus,
    RunTrigger,
)
from app.models.schemas import RepairAttemptOut
from app.services.extraction_service import run_extraction
from app.services.repair_engine import RepairResult
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
        was_repaired=updates.get("was_repaired", False),
        credits_used=updates.get("credits_used", 0),
        error=updates.get("error"),
    )


def _mock_run_patches(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
    finalize_mock: AsyncMock,
):
    return (
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
            "app.services.extraction_service.record_run_outcome",
            new=AsyncMock(),
        ),
    )


@contextmanager
def _mocked_extraction(*patchers):
    entered = [patcher.__enter__() for patcher in patchers]
    try:
        yield entered
    finally:
        for patcher in reversed(patchers):
            patcher.__exit__(None, None, None)


@pytest.mark.asyncio
async def test_run_extraction_completed_when_mocked_agent_matches_schema(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))

    with _mocked_extraction(
        *_mock_run_patches(sample_extractor, running_run, finalize_mock),
        patch(
            "app.services.extraction_service.run_agent",
            return_value=(RunStatus.COMPLETED, VALID_AGENT_DATA, 5, None),
        ),
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.COMPLETED
    assert result.validation_errors == []
    assert result.error is None
    assert result.data == VALID_AGENT_DATA
    assert result.was_repaired is False
    assert result.repair_attempts == []

    finalize_mock.assert_awaited_once()
    updates = finalize_mock.await_args.args[1]
    assert updates["status"] == RunStatus.COMPLETED.value
    assert updates["validation_errors"] == []


@pytest.mark.asyncio
async def test_run_extraction_failed_when_validation_and_repair_exhausted(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))
    repair_errors = ["'shoes' is a required property"]
    repair_result = RepairResult(
        succeeded=False,
        data=INVALID_AGENT_DATA,
        validation_errors=repair_errors,
        repair_attempts=[
            RepairAttemptOut(
                id="repair-1",
                run_id=RUN_ID,
                strategy=RepairStrategy.PROMPT_REFINEMENT,
                succeeded=False,
                prompt_used="refined prompt",
                model_used="spark-1-mini",
                data=INVALID_AGENT_DATA,
                error=None,
                duration_ms=100,
                credits_used=2,
            )
        ],
        credits_used=2,
    )

    with _mocked_extraction(
        *_mock_run_patches(sample_extractor, running_run, finalize_mock),
        patch(
            "app.services.extraction_service.run_agent",
            return_value=(RunStatus.COMPLETED, INVALID_AGENT_DATA, 5, None),
        ),
        patch(
            "app.services.extraction_service.attempt_repair",
            new=AsyncMock(return_value=repair_result),
        ),
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.FAILED
    assert result.validation_errors == repair_errors
    assert result.error is not None
    assert "auto-repair exhausted" in result.error
    assert result.data == INVALID_AGENT_DATA
    assert len(result.repair_attempts) == 1

    updates = finalize_mock.await_args.args[1]
    assert updates["status"] == RunStatus.FAILED.value


@pytest.mark.asyncio
async def test_run_extraction_repaired_when_auto_repair_succeeds(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))
    repair_result = RepairResult(
        succeeded=True,
        data=VALID_AGENT_DATA,
        repair_attempts=[
            RepairAttemptOut(
                id="repair-1",
                run_id=RUN_ID,
                strategy=RepairStrategy.PROMPT_REFINEMENT,
                succeeded=True,
                prompt_used="refined prompt",
                model_used="spark-1-mini",
                data=VALID_AGENT_DATA,
                error=None,
                duration_ms=100,
                credits_used=2,
            )
        ],
        credits_used=2,
    )

    with _mocked_extraction(
        *_mock_run_patches(sample_extractor, running_run, finalize_mock),
        patch(
            "app.services.extraction_service.run_agent",
            return_value=(RunStatus.COMPLETED, INVALID_AGENT_DATA, 5, None),
        ),
        patch(
            "app.services.extraction_service.attempt_repair",
            new=AsyncMock(return_value=repair_result),
        ),
        patch(
            "app.services.extraction_service.update_model_preference",
            new=AsyncMock(),
        ),
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.REPAIRED
    assert result.was_repaired is True
    assert result.validation_errors == []
    assert result.error is None
    assert result.data == VALID_AGENT_DATA
    assert result.credits_used == 7
    assert len(result.repair_attempts) == 1

    updates = finalize_mock.await_args.args[1]
    assert updates["status"] == RunStatus.REPAIRED.value
    assert updates["was_repaired"] is True


@pytest.mark.asyncio
async def test_run_extraction_does_not_validate_when_agent_fails(
    sample_extractor: ExtractorRow,
    running_run: ExtractionRunRow,
) -> None:
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))
    finalize_mock = AsyncMock(side_effect=lambda _run_id, updates: _build_finalized_run(updates))
    p1, p2, p3, p4 = _mock_run_patches(sample_extractor, running_run, finalize_mock)

    with (
        p1,
        p2,
        p3,
        p4,
        patch(
            "app.services.extraction_service.run_agent",
            return_value=(RunStatus.FAILED, None, 0, "Agent timed out"),
        ),
        patch(
            "app.services.extraction_service.validate_extraction",
        ) as validate_mock,
        patch(
            "app.services.extraction_service.attempt_repair",
            new=AsyncMock(),
        ) as repair_mock,
    ):
        result = await run_extraction(EXTRACTOR_ID)

    assert result.status == RunStatus.FAILED
    assert result.validation_errors == []
    assert result.error == "Agent timed out"
    validate_mock.assert_not_called()
    repair_mock.assert_not_awaited()
