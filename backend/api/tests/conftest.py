from datetime import datetime, timezone

import pytest

from app.models.db_models import (
    AgentModel,
    ExtractorHealth,
    ExtractorRow,
    ExtractorStatus,
    ExtractionRunRow,
    RunStatus,
    RunTrigger,
)

NOW = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
EXTRACTOR_ID = "c37647d7-8c5c-4790-8231-e9ac0fe17347"
RUN_ID = "ca11fc6b-3e1d-470d-af5e-ae3141f10693"

VALID_SHOES_DATA = {
    "shoes": [
        {
            "name": "Air Jordan 5",
            "category": "Men's Shoes",
            "price": 220,
        }
    ]
}


@pytest.fixture
def shoes_schema() -> dict:
    return {
        "type": "object",
        "required": ["shoes"],
        "properties": {
            "shoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "category", "price"],
                    "properties": {
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "price": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
            }
        },
        "additionalProperties": False,
    }


@pytest.fixture
def sample_extractor(shoes_schema: dict) -> ExtractorRow:
    return ExtractorRow(
        id=EXTRACTOR_ID,
        name="Shoe Product Extractor",
        urls=["https://www.nike.com/w/mens-shoes-nik1zy7ok"],
        prompt="Extract every shoe on the page into the shoes array.",
        schema_definition=shoes_schema,
        status=ExtractorStatus.ACTIVE,
        health=ExtractorHealth.HEALTHY,
        model_preference=AgentModel.SPARK_1_MINI,
        consecutive_failures=0,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def running_run() -> ExtractionRunRow:
    return ExtractionRunRow(
        id=RUN_ID,
        extractor_id=EXTRACTOR_ID,
        status=RunStatus.RUNNING,
        trigger=RunTrigger.MANUAL,
        started_at=NOW,
    )
