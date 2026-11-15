from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "spec"


@lru_cache(maxsize=4)
def _validator(name: str) -> Draft202012Validator:
    path = SCHEMA_DIR / name
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _as_payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if not isinstance(value, dict):
        raise TypeError("Schema validation requires a model or object.")
    return value


def validate_event(value: Any) -> None:
    """Raise jsonschema.ValidationError unless a minimized event meets the versioned contract."""
    _validator("event.schema.json").validate(_as_payload(value))


def validate_evidence_manifest(value: Any) -> None:
    """Raise jsonschema.ValidationError unless an evidence manifest meets its contract."""
    _validator("evidence.schema.json").validate(_as_payload(value))
