from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FindingState(str, Enum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE = "inconclusive"
    NOT_REPRODUCIBLE = "not_reproducible"


class TestRequest(StrictModel):
    scope_id: str = Field(default="local-synthetic", min_length=1, max_length=64)
    batch_size: int = Field(default=20, ge=1, le=200)
    seed: int = Field(default=7, ge=0, le=2**31 - 1)


class TestObservation(StrictModel):
    test_id: str = Field(min_length=1, max_length=128)
    property_id: str = Field(pattern=r"^[A-Z][A-Z0-9_-]{2,63}$")
    outcome: str = Field(min_length=1, max_length=64)
    latency_ms: float = Field(ge=0, allow_inf_nan=False)
    attributes: dict[str, Any] = Field(default_factory=dict)


class RunRecord(StrictModel):
    run_id: str = Field(default_factory=lambda: str(uuid4()))
    scope_id: str
    status: str
    created_at: datetime = Field(default_factory=utcnow)
    observations: list[TestObservation] = Field(default_factory=list)
    candidate_count: int = 0
    validated_count: int = 0
    evidence_ids: list[str] = Field(default_factory=list)


class Finding(StrictModel):
    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    property_id: str
    state: FindingState
    anomaly_score: float = Field(ge=0, allow_inf_nan=False)
    security_impact: str
    expected: str
    actual: str
    rationale: str
    created_at: datetime = Field(default_factory=utcnow)
    evidence_id: str | None = None


class EvidenceRecord(StrictModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    finding_id: str
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    manifest: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)
