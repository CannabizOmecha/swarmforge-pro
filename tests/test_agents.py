import asyncio

import pytest
from pydantic import ValidationError

from aegis.agent_runtime import (
    AdapterResponse,
    AgentCapabilityError,
    AgentContractError,
    AgentInputError,
    AgentPipelineRequest,
    AgentStatus,
    AgentTask,
    AgentTaskType,
    AgentToolbox,
    Capability,
    DeterministicMockAdapter,
    candidate_digest,
    execute_agent_task,
    execute_validation_pipeline,
)


def test_task_routes_to_fixed_least_privilege_expert():
    result = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.INSPECT_FIXTURE,
                payload={"fixture_id": "authz-deny-v1"},
            )
        )
    )
    assert result.expert_name == "test_generator"
    assert result.status == AgentStatus.COMPLETED
    assert result.capabilities_used == [Capability.READ_SYNTHETIC_FIXTURE]
    assert result.output["expected_decision"] == "deny"
    assert result.adapter_mode == "deterministic_mock"


def test_validator_is_separate_and_confirms_only_explicit_fixture_violation():
    denied = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.VALIDATE_FIXTURE,
                payload={"fixture_id": "authz-deny-v1", "observed_decision": "deny"},
            )
        )
    )
    allowed = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.VALIDATE_FIXTURE,
                payload={"fixture_id": "authz-deny-v1", "observed_decision": "allow"},
            )
        )
    )
    assert denied.expert_name == "security_validator"
    assert denied.output["security_property_passed"] is True
    assert denied.output["violation_confirmed"] is False
    assert allowed.output["security_property_passed"] is False
    assert allowed.output["violation_confirmed"] is True
    assert Capability.VALIDATE_SYNTHETIC_ASSERTION in allowed.capabilities_used


def test_critic_is_distinct_and_checks_candidate_contract():
    unsigned = {
        "property_id": "AUTHZ-001",
        "expected": "deny",
        "actual": "allow",
        "scope_id": "local-synthetic",
    }
    candidate = {**unsigned, "candidate_sha256": candidate_digest(unsigned)}
    result = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.CRITIQUE_CANDIDATE,
                payload={"candidate": candidate},
            )
        )
    )
    assert result.expert_name == "critic"
    assert result.output == {"accepted": True, "issues": []}
    assert result.capabilities_used == [Capability.REVIEW_CANDIDATE]


def test_strict_task_payload_rejects_extra_fields():
    with pytest.raises(AgentInputError):
        asyncio.run(
            execute_agent_task(
                AgentTask(
                    task_type=AgentTaskType.INSPECT_FIXTURE,
                    payload={"fixture_id": "authz-deny-v1", "url": "https://example.com"},
                )
            )
        )


def test_task_request_rejects_out_of_bounds_deadline_and_unknown_fields():
    with pytest.raises(ValidationError):
        AgentTask(
            task_type=AgentTaskType.INSPECT_FIXTURE,
            payload={"fixture_id": "authz-deny-v1"},
            deadline_ms=10000,
        )
    with pytest.raises(ValidationError):
        AgentTask(
            task_type=AgentTaskType.INSPECT_FIXTURE,
            payload={"fixture_id": "authz-deny-v1"},
            model_provider="unapproved",
        )


def test_toolbox_denies_ungranted_capability():
    tools = AgentToolbox(frozenset({Capability.READ_SYNTHETIC_FIXTURE}))
    with pytest.raises(AgentCapabilityError):
        tools.validate_assertion("authz-deny-v1", "allow")
    with pytest.raises(AgentCapabilityError):
        tools.review_candidate({"scope_id": "local-synthetic"})


def test_unknown_fixture_is_rejected():
    with pytest.raises(AgentInputError):
        asyncio.run(
            execute_agent_task(
                AgentTask(
                    task_type=AgentTaskType.INSPECT_FIXTURE,
                    payload={"fixture_id": "untrusted-fixture"},
                )
            )
        )


def test_deadline_causes_abstention_not_unbounded_execution():
    class SlowAdapter(DeterministicMockAdapter):
        async def execute(self, payload, tools):
            await asyncio.sleep(0.1)
            return await super().execute(payload, tools)

    task = AgentTask(
        task_type=AgentTaskType.INSPECT_FIXTURE,
        payload={"fixture_id": "authz-deny-v1"},
        deadline_ms=10,
    )
    result = asyncio.run(
        execute_agent_task(task, {"test_generator": SlowAdapter("test_generator")})
    )
    assert result.status == AgentStatus.ABSTAINED
    assert result.abstention_reason == "deadline_exceeded"


def test_adapter_output_budget_is_enforced():
    class OversizedAdapter(DeterministicMockAdapter):
        async def execute(self, payload, tools):
            return AdapterResponse(
                status=AgentStatus.COMPLETED,
                output={"large": "x" * 500},
            )

    task = AgentTask(
        task_type=AgentTaskType.INSPECT_FIXTURE,
        payload={"fixture_id": "authz-deny-v1"},
        max_output_bytes=128,
    )
    with pytest.raises(AgentContractError):
        asyncio.run(
            execute_agent_task(
                task, {"test_generator": OversizedAdapter("test_generator")}
            )
        )


def test_adapter_failure_abstains_without_exposing_exception_text():
    class BrokenAdapter(DeterministicMockAdapter):
        async def execute(self, payload, tools):
            raise RuntimeError("sensitive diagnostic string")

    result = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.INSPECT_FIXTURE,
                payload={"fixture_id": "authz-deny-v1"},
            ),
            {"test_generator": BrokenAdapter("test_generator")},
        )
    )
    assert result.status == AgentStatus.ABSTAINED
    assert result.abstention_reason == "adapter_error"
    assert "sensitive" not in str(result.model_dump())


def test_critic_rejects_candidate_digest_tampering():
    candidate = {
        "property_id": "AUTHZ-001",
        "expected": "deny",
        "actual": "allow",
        "scope_id": "local-synthetic",
        "candidate_sha256": "0" * 64,
    }
    result = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.CRITIQUE_CANDIDATE,
                payload={"candidate": candidate},
            )
        )
    )
    assert result.output["accepted"] is False
    assert "candidate_digest_mismatch" in result.output["issues"]


def test_three_expert_pipeline_runs_generator_validator_and_independent_critic():
    result = asyncio.run(
        execute_validation_pipeline(
            AgentPipelineRequest(
                fixture_id="authz-deny-v1",
                observed_decision="allow",
            )
        )
    )
    assert result.status == AgentStatus.COMPLETED
    assert [stage.expert_name for stage in result.stages] == [
        "test_generator",
        "security_validator",
        "critic",
    ]
    assert result.summary["violation_confirmed"] is True
    assert result.summary["critic_accepted"] is True
    assert result.summary["persistence"] == "not_performed"


def test_three_expert_pipeline_accepts_expected_deny_without_finding():
    result = asyncio.run(
        execute_validation_pipeline(
            AgentPipelineRequest(
                fixture_id="authz-deny-v1",
                observed_decision="deny",
            )
        )
    )
    assert result.status == AgentStatus.COMPLETED
    assert result.summary["security_property_passed"] is True
    assert result.summary["violation_confirmed"] is False


def test_pipeline_stops_when_independent_validator_abstains():
    class AbstainingValidator(DeterministicMockAdapter):
        async def execute(self, payload, tools):
            return AdapterResponse(
                status=AgentStatus.ABSTAINED,
                abstention_reason="test_abstention",
            )

    result = asyncio.run(
        execute_validation_pipeline(
            AgentPipelineRequest(
                fixture_id="authz-deny-v1",
                observed_decision="allow",
            ),
            {
                "test_generator": DeterministicMockAdapter("test_generator"),
                "security_validator": AbstainingValidator("security_validator"),
                "critic": DeterministicMockAdapter("critic"),
            },
        )
    )
    assert result.status == AgentStatus.ABSTAINED
    assert [stage.expert_name for stage in result.stages] == [
        "test_generator",
        "security_validator",
    ]
    assert result.summary["stopped_after"] == "security_validator"


def test_abstention_metrics_use_only_registered_reason_labels():
    from aegis.observability import RELIABILITY_METRICS

    before = RELIABILITY_METRICS.snapshot()

    class SlowAdapter(DeterministicMockAdapter):
        async def execute(self, payload, tools):
            await asyncio.sleep(0.1)
            return await super().execute(payload, tools)

    result = asyncio.run(
        execute_agent_task(
            AgentTask(
                task_type=AgentTaskType.INSPECT_FIXTURE,
                payload={"fixture_id": "authz-deny-v1"},
                deadline_ms=10,
            ),
            {"test_generator": SlowAdapter("test_generator")},
        )
    )
    assert result.status == AgentStatus.ABSTAINED
    after = RELIABILITY_METRICS.snapshot()
    assert after["expert_abstentions"]["deadline_exceeded"] == (
        before["expert_abstentions"]["deadline_exceeded"] + 1
    )
