from __future__ import annotations

from typing import Any

from .engine import canonical_hash
from .models import Finding

FINGERPRINT_VERSION = "aegis.finding.v1"


def _normalize(value: str) -> str:
    """Normalize presentation-only whitespace and case for semantic grouping."""
    return " ".join(value.split()).casefold()


def finding_fingerprint(finding: Finding) -> str:
    """Return a stable semantic fingerprint that excludes run-specific identifiers."""
    payload: dict[str, Any] = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "property_id": finding.property_id.strip().upper(),
        "state": finding.state.value,
        "security_impact": _normalize(finding.security_impact),
        "expected": _normalize(finding.expected),
        "actual": _normalize(finding.actual),
    }
    return canonical_hash(payload)
