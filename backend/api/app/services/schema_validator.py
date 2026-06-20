from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


def _format_error(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def validate_extraction(
    data: dict[str, Any] | None,
    schema: dict[str, Any],
) -> list[str]:
    """
    Validate agent output against the extractor's JSON Schema.

    Returns a list of human-readable error messages. An empty list means valid.
    """
    if data is None:
        return ["No data returned from agent"]

    if not isinstance(data, dict):
        return [f"Expected object, got {type(data).__name__}"]

    try:
        validator = Draft202012Validator(schema)
    except SchemaError as exc:
        return [f"Invalid extractor schema: {exc.message}"]

    errors = sorted(validator.iter_errors(data), key=lambda err: list(err.absolute_path))
    return [_format_error(err) for err in errors]
