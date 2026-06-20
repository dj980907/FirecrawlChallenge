from app.services.schema_validator import validate_extraction


def test_validate_extraction_passes_for_matching_data(shoes_schema: dict) -> None:
    data = {
        "shoes": [
            {
                "name": "Air Jordan 5",
                "category": "Men's Shoes",
                "price": 220,
            }
        ]
    }

    assert validate_extraction(data, shoes_schema) == []


def test_validate_extraction_fails_when_required_field_missing(shoes_schema: dict) -> None:
    data = {
        "name": "Air Jordan 5",
        "category": "Men's Shoes",
        "price": 220,
    }

    errors = validate_extraction(data, shoes_schema)

    assert errors
    assert any("shoes" in error for error in errors)


def test_validate_extraction_fails_when_data_is_none(shoes_schema: dict) -> None:
    assert validate_extraction(None, shoes_schema) == ["No data returned from agent"]
