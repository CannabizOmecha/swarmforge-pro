# AEGIS-MoE Orchestration Contract

## Execution models
The local MVP contains two deliberately separate execution paths:
- A durable, sequential synthetic assurance workflow backed by SQLite.
- An in-memory, deterministic three-expert demonstration pipeline backed by strict adapter contracts.

Neither path is a distributed workflow service or a live LLM swarm.

## Durable synthetic workflow
1. ACCEPTED — request, canonical fingerprint, and optional idempotency key are durably registered.
2. AUTHORIZED — fixed local-synthetic scope and operation budget pass the fail-closed policy check.
3. EXECUTED — observations, findings, and evidence are checkpointed as one stage payload.
4. COMMITTED — run, findings, evidence, response cache, and completion state commit in one SQLite transaction.
5. REJECTED — authorization failed; terminal state.
6. EXHAUSTED — bounded three-attempt execution budget consumed.

Each transition uses compare-and-set against the expected prior state. Same-key/same-request calls resume or return the original result; same-key/different-request calls return HTTP 409. Execution failures leave the workflow at AUTHORIZED. A saved EXECUTED checkpoint can be committed without rerunning the generator. A crash after execution returns but before checkpoint persistence may cause deterministic execution to run again: at-least-once before checkpoint, not exactly-once. SQLite state is single-host only.

## Deterministic expert pipeline
`POST /agent-pipelines/validate` runs:
1. test_generator inspects a fixed fixture and returns its expected decision.
2. security_validator independently evaluates the observed decision against the fixture invariant.
3. critic checks candidate structure, local-synthetic scope, and canonical candidate SHA-256 digest.

Each stage is assigned by task type. The caller cannot choose the expert or request capabilities. Each adapter receives only a static grant through a narrow toolbox. Per-task deadline, input/output size limits, strict result validation, and abstention are enforced. The pipeline stops on abstention or rejection.

The pipeline does not persist a finding or evidence. Its candidate digest is an integrity check on the in-memory candidate, not an evidence identifier. Persistent evidence generation remains in the durable `POST /runs` workflow.

## Governance policy
- Python authorization is the runtime enforcement boundary and uses an immutable, startup-validated local-synthetic registry.
- Rego policy version 1.0.0 is SHA-256 pinned by spec/policy-manifest.json.
- CI installs OPA 1.22.4 from the official static release, verifies its binary digest, checks Rego formatting/compilation, and runs nine positive/negative tests.
- OPA is not called by the API at runtime; the Rego artifact is independently tested and Python authorization remains authoritative.

## Audit events
Workflow acceptance, state transitions, attempts, failures, rejection, commit, resume requests, and expert/pipeline outcomes append sanitized events to a local SHA-256 hash chain. Audit events are written in the same transaction as the associated workflow transition or final bundle where applicable. Agent events record task type, expert, status, and capabilities used; raw task payloads are not recorded. GET /audit/verify checks sequence continuity and all hashes. SQLite triggers block normal updates/deletes. This is tamper-evident only; it is not a signature, remote WORM store, or protection against a privileged database administrator.

## Recovery semantics
- A client idempotency key is bound to a canonical request fingerprint.
- Legacy idempotency rows are honored across the workflow migration.
- Execution attempts are bounded to three.
- Commit failures preserve the EXECUTED checkpoint.
- Final bundle persistence and transition to COMMITTED are one transaction.
- Evidence verification revalidates schema and recomputes the digest; mismatches are never repaired automatically.

## Failure semantics
- Unknown scope and unauthorized operations fail closed.
- Invalid request shape is rejected before workflow creation.
- Invalid telemetry or evidence manifests fail before checkpoint/persistence.
- Transient execution errors are recorded with sanitized codes.
- Expert timeout or adapter error yields an abstention; malformed adapter output or capability escalation fails the adapter contract.
- Missing run, workflow, or evidence identifiers return 404.

## Production blockers
Authentication/authorization for multi-user access, general migrations, encrypted key management, immutable external evidence storage, distributed workflow engine, OpenTelemetry backend, live independent model agents, operational SLOs, and deployment security review are not implemented. Keep the API bound to loopback.
