from __future__ import annotations

import asyncio
import json
from enum import StrEnum
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .policy import AuthorizationError, authorize


class AgentTaskType(StrEnum):
    INSPECT_FIXTURE = "inspect_fixture"
    VALIDATE_FIXTURE = "validate_fixture"
    CRITIQUE_CANDIDATE = "critique_candidate"


class AgentStatus(StrEnum):
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    REJECTED = "rejected"


class Capability(StrEnum):
    READ_SYNTHETIC_FIXTURE = "read_synthetic_fixture"
    VALIDATE_SYNTHETIC_ASSERTION = "validate_synthetic_assertion"
    REVIEW_CANDIDATE = "review_candidate"


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentTask(StrictContract):
    task_id: UUID = Field(default_factory=uuid4)
    scope_id: Literal["local-synthetic"] = "local-synthetic"
    task_type: AgentTaskType
    payload: dict[str, Any]
    deadline_ms: int = Field(default=250, ge=10, le=2000)
    max_output_bytes: int = Field(default=4096, ge=128, le=8192)


class AgentResult(StrictContract):
    task_id: UUID
    task_type: AgentTaskType
    expert_name: str
    status: AgentStatus
    output: dict[str, Any] = Field(default_factory=dict)
    capabilities_used: list[Capability] = Field(default_factory=list)
    adapter_mode: Literal["deterministic_mock"]
    duration_ms: int = Field(ge=0)
    abstention_reason: str | None = Field(default=None, max_length=96)


class AdapterResponse(StrictContract):
    status: AgentStatus
    output: dict[str, Any] = Field(default_factory=dict)
    abstention_reason: str | None = Field(default=None, max_length=96)


class InspectFixturePayload(StrictContract):
    fixture_id: Literal["authz-deny-v1", "authz-allow-v1"]


class ValidateFixturePayload(StrictContract):
    fixture_id: Literal["authz-deny-v1"]
    observed_decision: Literal["allow", "deny"]


class CritiqueCandidatePayload(StrictContract):
    candidate: dict[str, Any] = Field(max_length=16)


PAYLOAD_MODELS: dict[AgentTaskType, type[BaseModel]] = {
    AgentTaskType.INSPECT_FIXTURE: InspectFixturePayload,
    AgentTaskType.VALIDATE_FIXTURE: ValidateFixturePayload,
    AgentTaskType.CRITIQUE_CANDIDATE: CritiqueCandidatePayload,
}

TASK_EXPERTS: dict[AgentTaskType, str] = {
    AgentTaskType.INSPECT_FIXTURE: "test_generator",
    AgentTaskType.VALIDATE_FIXTURE: "security_validator",
    AgentTaskType.CRITIQUE_CANDIDATE: "critic",
}

EXPERT_CAPABILITIES: dict[str, frozenset[Capability]] = {
    "test_generator": frozenset({Capability.READ_SYNTHETIC_FIXTURE}),
    "security_validator": frozenset(
        {
            Capability.READ_SYNTHETIC_FIXTURE,
            Capability.VALIDATE_SYNTHETIC_ASSERTION,
        }
    ),
    "critic": frozenset({Capability.REVIEW_CANDIDATE}),
}

FIXTURES: dict[str, dict[str, str]] = {
    "authz-deny-v1": {
        "fixture_id": "authz-deny-v1",
        "property_id": "AUTHZ-001",
        "expected_decision": "deny",
        "fixture_version": "1",
    },
    "authz-allow-v1": {
        "fixture_id": "authz-allow-v1",
        "property_id": "AUTHZ-002",
        "expected_decision": "allow",
        "fixture_version": "1",
    },
}


class AgentInputError(ValueError):
    pass


class AgentContractError(RuntimeError):
    pass


class AgentCapabilityError(PermissionError):
    pass


class AgentToolbox:
    """Only exposes fixed, read-only synthetic fixture operations."""

    def __init__(self, granted: frozenset[Capability]):
        self._granted = granted
        self._used: set[Capability] = set()

    @property
    def used(self) -> list[Capability]:
        return sorted(self._used, key=lambda item: item.value)

    def _require(self, capability: Capability) -> None:
        if capability not in self._granted:
            raise AgentCapabilityError("Capability is not granted to this expert.")
        self._used.add(capability)

    def read_fixture(self, fixture_id: str) -> dict[str, str]:
        self._require(Capability.READ_SYNTHETIC_FIXTURE)
        fixture = FIXTURES.get(fixture_id)
        if fixture is None:
            raise AgentInputError("Unknown synthetic fixture.")
        return dict(fixture)

    def validate_assertion(self, fixture_id: str, observed_decision: str) -> dict[str, Any]:
        self._require(Capability.VALIDATE_SYNTHETIC_ASSERTION)
        fixture = self.read_fixture(fixture_id)
        expected = fixture["expected_decision"]
        passed = observed_decision == expected
        return {
            "property_id": fixture["property_id"],
            "expected_decision": expected,
            "observed_decision": observed_decision,
            "security_property_passed": passed,
            "violation_confirmed": not passed,
            "scope_id": "local-synthetic",
        }

    def review_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        self._require(Capability.REVIEW_CANDIDATE)
        required = {"property_id", "expected", "actual", "evidence_id", "scope_id"}
        issues = sorted(required.difference(candidate))
        if candidate.get("scope_id") != "local-synthetic":
            issues.append("scope_not_local_synthetic")
        return {"accepted": not issues, "issues": issues}


class ExpertAdapter(Protocol):
    name: str
    mode: str

    async def execute(self, payload: BaseModel, tools: AgentToolbox) -> AdapterResponse:
        ...


class DeterministicMockAdapter:
    mode = "deterministic_mock"

    def __init__(self, name: str):
        if name not in EXPERT_CAPABILITIES:
            raise ValueError("Unknown expert adapter.")
        self.name = name

    async def execute(self, payload: BaseModel, tools: AgentToolbox) -> AdapterResponse:
        if self.name == "test_generator":
            typed = InspectFixturePayload.model_validate(payload)
            fixture = tools.read_fixture(typed.fixture_id)
            return AdapterResponse(
                status=AgentStatus.COMPLETED,
                output={
                    "fixture_id": fixture["fixture_id"],
                    "property_id": fixture["property_id"],
                    "expected_decision": fixture["expected_decision"],
                    "fixture_version": fixture["fixture_version"],
                },
            )

        if self.name == "security_validator":
            typed = ValidateFixturePayload.model_validate(payload)
            result = tools.validate_assertion(typed.fixture_id, typed.observed_decision)
            return AdapterResponse(status=AgentStatus.COMPLETED, output=result)

        if self.name == "critic":
            typed = CritiqueCandidatePayload.model_validate(payload)
            result = tools.review_candidate(typed.candidate)
            return AdapterResponse(status=AgentStatus.COMPLETED, output=result)

        return AdapterResponse(status=AgentStatus.ABSTAINED, abstention_reason="unsupported_task")


DEFAULT_ADAPTERS: dict[str, ExpertAdapter] = {
    name: DeterministicMockAdapter(name) for name in EXPERT_CAPABILITIES
}


async def execute_agent_task(
    task: AgentTask,
    adapters: dict[str, ExpertAdapter] | None = None,
) -> AgentResult:
    """Execute one bounded task using its statically assigned least-privilege expert."""
    try:
        authorize(task.scope_id, "validate", 1)
    except AuthorizationError:
        return AgentResult(
            task_id=task.task_id,
            task_type=task.task_type,
            expert_name=TASK_EXPERTS[task.task_type],
            status=AgentStatus.REJECTED,
            adapter_mode="deterministic_mock",
            duration_ms=0,
            abstention_reason="scope_not_authorized",
        )

    try:
        payload_model = PAYLOAD_MODELS[task.task_type].model_validate(task.payload)
        payload_bytes = json.dumps(
            payload_model.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (ValidationError, TypeError, ValueError) as exc:
        raise AgentInputError("Task payload does not match its strict contract.") from exc

    if len(payload_bytes) > 8192:
        raise AgentInputError("Task payload exceeds the input size budget.")

    expert_name = TASK_EXPERTS[task.task_type]
    granted = EXPERT_CAPABILITIES[expert_name]
    toolbox = AgentToolbox(granted)
    adapter = (adapters or DEFAULT_ADAPTERS).get(expert_name)
    if adapter is None or adapter.name != expert_name or adapter.mode != "deterministic_mock":
        raise AgentContractError("No compatible adapter is registered for this task.")

    started = perf_counter()
    try:
        raw_response = await asyncio.wait_for(
            adapter.execute(payload_model, toolbox),
            timeout=task.deadline_ms / 1000,
        )
        response = AdapterResponse.model_validate(raw_response)
    except TimeoutError:
        return AgentResult(
            task_id=task.task_id,
            task_type=task.task_type,
            expert_name=expert_name,
            status=AgentStatus.ABSTAINED,
            capabilities_used=toolbox.used,
            adapter_mode="deterministic_mock",
            duration_ms=int((perf_counter() - started) * 1000),
            abstention_reason="deadline_exceeded",
        )
    except AgentCapabilityError as exc:
        raise AgentContractError("Adapter attempted an ungranted capability.") from exc
    except AgentContractError:
        raise
    except ValidationError as exc:
        raise AgentContractError("Adapter returned an invalid result schema.") from exc
    except Exception:  # noqa: BLE001 - adapter boundary fails closed to abstention.
        return AgentResult(
            task_id=task.task_id,
            task_type=task.task_type,
            expert_name=expert_name,
            status=AgentStatus.ABSTAINED,
            capabilities_used=toolbox.used,
            adapter_mode="deterministic_mock",
            duration_ms=int((perf_counter() - started) * 1000),
            abstention_reason="adapter_error",
        )

    try:
        output_bytes = json.dumps(
            response.output,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AgentContractError("Adapter output is not valid finite JSON.") from exc

    if len(output_bytes) > task.max_output_bytes:
        raise AgentContractError("Adapter output exceeded its declared size budget.")

    return AgentResult(
        task_id=task.task_id,
        task_type=task.task_type,
        expert_name=expert_name,
        status=response.status,
        output=response.output,
        capabilities_used=toolbox.used,
        adapter_mode="deterministic_mock",
        duration_ms=int((perf_counter() - started) * 1000),
        abstention_reason=response.abstention_reason,
    )
