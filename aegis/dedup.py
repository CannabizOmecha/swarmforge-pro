from __future__ import annotations

from typing import Any

from .engine import canonical_hash
from .models import Finding

FINGERPRINT_VERSION = "aegis.finding.v1"


def _normalize_impact(value: str) -> str:
    """Normalize the controlled impact label without altering observed semantics."""
    return value.strip().casefold()


def finding_fingerprint(finding: Finding) -> str:
    """Return a stable semantic fingerprint that excludes run-specific identifiers."""
    payload: dict[str, Any] = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "property_id": finding.property_id.strip().upper(),
        "state": finding.state.value,
        "security_impact": _normalize_impact(finding.security_impact),
        # Preserve case and internal whitespace: observed values can be case-sensitive.
        "expected": finding.expected.strip(),
        "actual": finding.actual.strip(),
    }
    return canonical_hash(payload)
