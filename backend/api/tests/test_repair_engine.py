from unittest.mock import AsyncMock, patch

import pytest

from app.models.db_models import AgentModel, RepairAttemptRow, RepairStrategy
from app.services.repair_engine import attempt_repair
from tests.conftest import EXTRACTOR_ID, RUN_ID, VALID_SHOES_DATA

VALID_AGENT_DATA = VALID_SHOES_DATA

INVALID_AGENT_DATA = {
    "name": "Air Jordan 5",
    "category": "Men's Shoes",
    "price": 220,
}


@pytest.mark.asyncio
async def test_attempt_repair_succeeds_on_first_strategy(
    sample_extractor,
) -> None:
    validation_errors = ["'shoes' is a required property"]
    attempt_row = RepairAttemptRow(
        id="repair-1",
        run_id=RUN_ID,
        strategy=RepairStrategy.PROMPT_REFINEMENT,
        succeeded=True,
        prompt_used="refined",
        model_used="spark-1-mini",
        data=VALID_AGENT_DATA,
        error=None,
        duration_ms=50,
        credits_used=2,
    )

    with (
        patch(
            "app.services.repair_engine.run_agent",
            return_value=(None, VALID_AGENT_DATA, 2, None),
        ),
        patch(
            "app.services.repair_engine.create_repair_attempt",
            new=AsyncMock(return_value=attempt_row),
        ),
    ):
        result = await attempt_repair(
            sample_extractor,
            RUN_ID,
            validation_errors,
            INVALID_AGENT_DATA,
        )

    assert result.succeeded is True
    assert result.data == VALID_AGENT_DATA
    assert len(result.repair_attempts) == 1
    assert result.repair_attempts[0].strategy == RepairStrategy.PROMPT_REFINEMENT


@pytest.mark.asyncio
async def test_attempt_repair_tries_model_upgrade_after_prompt_refinement_fails(
    sample_extractor,
) -> None:
    def make_attempt_row(strategy: RepairStrategy, succeeded: bool, data: dict) -> RepairAttemptRow:
        return RepairAttemptRow(
            id=f"repair-{strategy.value}",
            run_id=RUN_ID,
            strategy=strategy,
            succeeded=succeeded,
            prompt_used="prompt",
            model_used=(
                AgentModel.SPARK_1_PRO.value
                if strategy == RepairStrategy.MODEL_UPGRADE
                else AgentModel.SPARK_1_MINI.value
            ),
            data=data,
            error=None if succeeded else "validation failed",
            duration_ms=50,
            credits_used=2,
        )

    agent_results = [
        (None, INVALID_AGENT_DATA, 2, None),
        (None, VALID_AGENT_DATA, 3, None),
    ]

    with (
        patch(
            "app.services.repair_engine.run_agent",
            side_effect=agent_results,
        ),
        patch(
            "app.services.repair_engine.create_repair_attempt",
            side_effect=[
                make_attempt_row(RepairStrategy.PROMPT_REFINEMENT, False, INVALID_AGENT_DATA),
                make_attempt_row(RepairStrategy.MODEL_UPGRADE, True, VALID_AGENT_DATA),
            ],
        ),
    ):
        result = await attempt_repair(
            sample_extractor,
            RUN_ID,
            ["'shoes' is a required property"],
            INVALID_AGENT_DATA,
        )

    assert result.succeeded is True
    assert result.model_upgraded is True
    assert len(result.repair_attempts) == 2
    assert result.repair_attempts[1].strategy == RepairStrategy.MODEL_UPGRADE


@pytest.mark.asyncio
async def test_attempt_repair_exhausts_all_strategies(
    sample_extractor,
) -> None:
    def make_attempt_row(strategy: RepairStrategy) -> RepairAttemptRow:
        return RepairAttemptRow(
            id=f"repair-{strategy.value}",
            run_id=RUN_ID,
            strategy=strategy,
            succeeded=False,
            prompt_used="prompt",
            model_used="spark-1-mini",
            data=INVALID_AGENT_DATA,
            error="still invalid",
            duration_ms=50,
            credits_used=2,
        )

    with (
        patch(
            "app.services.repair_engine.run_agent",
            return_value=(None, INVALID_AGENT_DATA, 2, None),
        ),
        patch(
            "app.services.repair_engine.scrape_urls_markdown",
            return_value="page markdown",
        ),
        patch(
            "app.services.repair_engine.create_repair_attempt",
            side_effect=[
                make_attempt_row(RepairStrategy.PROMPT_REFINEMENT),
                make_attempt_row(RepairStrategy.MODEL_UPGRADE),
                make_attempt_row(RepairStrategy.FRESH_SCRAPE),
            ],
        ),
    ):
        result = await attempt_repair(
            sample_extractor,
            RUN_ID,
            ["'shoes' is a required property"],
            INVALID_AGENT_DATA,
        )

    assert result.succeeded is False
    assert len(result.repair_attempts) == 3
    assert result.credits_used == 6
