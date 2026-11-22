"""Serialize framework validation errors without adding validation rules."""

import json

from pydantic import ValidationError


def format_validation_error(error: ValidationError) -> str:
    """Convert a Pydantic failure to the JSON text expected by LangChain.

    Example (abridged): an error for limit=0 ->
    '{"status":"error","error":{"code":"INVALID_INPUT","details":[...]}}'.
    """
    details = [
        {
            "field": ".".join(map(str, item["loc"])) or "filters",
            "message": item["msg"],
        }
        for item in error.errors(
            include_url=False, include_context=False, include_input=False
        )
    ]
    return json.dumps(
        {"status": "error", "error": {"code": "INVALID_INPUT", "details": details}},
        separators=(",", ":"),
    )
