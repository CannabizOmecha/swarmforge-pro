from __future__ import annotations

import hashlib
import json
from typing import Any

from .baseline import robust_anomaly_score
from .experts import route
from .models import EvidenceRecord, Finding, FindingState, RunRecord, TestObservation
from .policy import authorize
from .privacy import minimize_attributes
from .validation import validate_event, validate_evidence_manifest

GENERATOR_VERSION = "aegis.synthetic.v1"


def canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _synthetic_latency(seed: int, index: int) -> float:
    material = f"{GENERATOR_VERSION}:{seed}:{index}".encode()
    digest = hashlib.sha256(material).digest()
    return float(100 + (int.from_bytes(digest[:4], "big") % 7) - 3)


def _replay_fingerprint(
    scope_id: str,
    batch_size: int,
    seed: int,
    observations: list[TestObservation],
    findings: list[Finding],
) -> str:
    semantic_observations = [
        {
            "property_id": item.property_id,
            "outcome": item.outcome,
            "latency_ms": item.latency_ms,
            "attributes": item.attributes,
        }
        for item in observations
    ]
    semantic_findings = [
        {
            "property_id": item.property_id,
            "state": item.state.value,
            "anomaly_score": item.anomaly_score,
            "security_impact": item.security_impact,
            "expected": item.expected,
            "actual": item.actual,
            "rationale": item.rationale,
        }
        for item in findings
    ]
    return canonical_hash(
        {
            "generator_version": GENERATOR_VERSION,
            "scope_id": scope_id,
            "batch_size": batch_size,
            "seed": seed,
            "observations": semantic_observations,
            "findings": semantic_findings,
        }
    )


def execute_synthetic_run(
    scope_id: str, batch_size: int, seed: int
) -> tuple[RunRecord, list[Finding], list[EvidenceRecord]]:
    scope = authorize(scope_id, "execute", batch_size)
    run = RunRecord(scope_id=scope.scope_id, status="completed", seed=seed)
    findings: list[Finding] = []
    evidence: list[EvidenceRecord] = []

    # Fixed synthetic reference distribution; the injected case is deterministic and harmless.
    reference_latency = [98.0, 101.0, 99.0, 102.0, 100.0, 97.0, 103.0, 100.0]
    observations: list[TestObservation] = []
    for index in range(batch_size):
        latency = _synthetic_latency(seed, index)
        outcome = "pass"
        property_id = "AUTHZ-001"
        attributes = {"operation": "synthetic_read", "status_code": 200, "outcome": outcome}
        if index == batch_size - 1 and batch_size >= 5:
            # Harmless fixture: a simulated policy assertion fails; no real access occurs.
            outcome = "simulated_policy_violation"
            latency = 101.0
            attributes["outcome"] = outcome
        observation = TestObservation(
            test_id=f"{run.run_id}-T{index + 1:04d}",
            property_id=property_id,
            outcome=outcome,
            latency_ms=latency,
            attributes=minimize_attributes(attributes),
        )
        validate_event(observation)
        observations.append(observation)

    for observation in observations:
        score = robust_anomaly_score(reference_latency, observation.latency_ms)
        if observation.outcome == "simulated_policy_violation":
            finding = Finding(
                run_id=run.run_id,
                property_id=observation.property_id,
                state=FindingState.VALIDATED,
                anomaly_score=score,
                security_impact="high",
                expected="Unauthorized synthetic principal is denied.",
                actual="Synthetic fixture returned simulated_policy_violation.",
                rationale=(
                    "The explicit AUTHZ-001 fixture assertion failed; this is a controlled "
                    "demonstration, not a real vulnerability."
                ),
            )
            manifest = {
                "run_id": run.run_id,
                "finding_id": finding.finding_id,
                "scope_id": scope_id,
                "environment": scope.environment,
                "property_id": finding.property_id,
                "test_id": observation.test_id,
                "expected": finding.expected,
                "actual": finding.actual,
                "generator": GENERATOR_VERSION,
                "seed": seed,
                "experts": route("run"),
                "observation": observation.model_dump(mode="json"),
            }
            validate_evidence_manifest(manifest)
            record = EvidenceRecord(
                run_id=run.run_id,
                finding_id=finding.finding_id,
                payload_sha256=canonical_hash(manifest),
                manifest=manifest,
            )
            finding.evidence_id = record.evidence_id
            findings.append(finding)
            evidence.append(record)

    run.observations = observations
    run.candidate_count = len(findings)
    run.validated_count = sum(f.state == FindingState.VALIDATED for f in findings)
    run.evidence_ids = [e.evidence_id for e in evidence]
    run.replay_fingerprint = _replay_fingerprint(
        scope_id, batch_size, seed, observations, findings
    )
    return run, findings, evidence
