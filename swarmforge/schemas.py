"""Typed contracts every agent must satisfy. Anything that fails validation is rejected, not guessed at."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Proposal(BaseModel):
    title: str = Field(max_length=200)
    rationale: str
    first_principles: list[str] = Field(description="Irreducible facts/constraints the proposal rests on")
    steps: list[str]
    risks: list[str]
    reversible: bool = Field(description="False if any step cannot be cheaply undone")
    confidence: float = Field(ge=0.0, le=1.0)


class Critique(BaseModel):
    fatal_flaws: list[str]
    weaknesses: list[str]
    hidden_assumptions: list[str]
    score: int = Field(ge=0, le=10, description="0 = unusable, 10 = robust")


class Verdict(BaseModel):
    chosen_index: int = Field(ge=0)
    why: str
    next_step: str = Field(description="One concrete, verifiable action")
    success_metric: str
    dissent: str = Field(description="Strongest argument against the choice")


class RunStatus(str, Enum):
    completed = "completed"            # recommendation ready, reversible
    awaiting_approval = "awaiting_approval"  # irreversible -> human must sign off
    approved = "approved"
    rejected = "rejected"
    failed = "failed"


class Expert(BaseModel):
    name: str
    lens: str


class ProposalRecord(BaseModel):
    expert: str
    proposal: Proposal | None = None
    critique: Critique | None = None
    error: str | None = None


class RunResult(BaseModel):
    id: str
    goal: str
    status: RunStatus
    proposals: list[ProposalRecord]
    verdict: Verdict | None = None
    chosen: Proposal | None = None
    error: str | None = None
    decided_by: Literal["swarm", "human"] = "swarm"
