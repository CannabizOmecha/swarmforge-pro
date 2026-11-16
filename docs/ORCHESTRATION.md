# AEGIS-MoE Orchestration Contract

## Execution model
The local MVP uses a deterministic, sequential workflow state machine backed by SQLite. The expert registry remains routing metadata and deterministic worker contracts, not proof of separately deployed LLM agents.

## Durable workflow states
1. ACCEPTED — the request, canonical request fingerprint, and optional client idempotency key are durably registered.
2. AUTHORIZED — the fixed local-synthetic scope and operation budget have passed the fail-closed policy check.
3. EXECUTED — generated observations, findings, and evidence are checkpointed as a single stage payload before final persistence.
4. COMMITTED — the run, findings, evidence, response cache, and workflow completion state are committed in one SQLite transaction.
5. REJECTED — authorization failed; the workflow is terminal.
6. EXHAUSTED — the bounded execution retry budget (three attempts) was consumed.

## Recovery semantics
- Each transition uses a compare-and-set update against the expected prior state.
- A client-supplied idempotency key is bound to a canonical request fingerprint. Same-key/same-request calls resume or return the original result; same-key/different-request calls return HTTP 409.
- Legacy idempotency rows created before the workflow-state migration are checked and honored, preventing a retry across the upgrade boundary from creating a duplicate run.
- Execution failure leaves the workflow at AUTHORIZED with a sanitized error code. A retry with the same idempotency key or POST /workflows/{workflow_id}/resume continues the same workflow.
- A successful execution is checkpointed at EXECUTED. If final persistence fails, resume commits the saved payload without rerunning the generator.
- Execution attempts are bounded to three. After the third failure the workflow becomes EXHAUSTED and will not execute again.
- Final bundle persistence and transition to COMMITTED are one transaction. A partial run/finding/evidence bundle cannot be reported as committed.
- A process crash after execution returns but before the EXECUTED checkpoint may cause the deterministic execution stage to run again. The generator is deterministic semantically; generated record identifiers are intentionally unique. This is at-least-once execution before checkpoint, not a claim of exactly-once execution.
- Workflows are local SQLite records. This is durable across process restarts on the same host and database, but not a distributed queue or multi-host workflow service.

## Run sequence
1. Governance resolves the immutable local-synthetic scope and operation budget.
2. Test generation creates bounded deterministic fixture cases using a versioned SHA-256-derived synthetic generator.
3. The synthetic executor performs in-process fixture work only; no network target exists.
4. Privacy applies an allowlist before telemetry is persisted.
5. Event schema validation checks every minimized event against the versioned JSON Schema contract.
6. Statistical scoring is independent from security-property validation.
7. Security validation checks the named synthetic property assertion; anomaly scores alone never validate a finding.
8. Evidence creation validates the canonical manifest and computes a SHA-256 digest.
9. The EXECUTED checkpoint is persisted.
10. Final persistence atomically commits the run, findings, evidence, response cache, and COMMITTED state.
11. Evidence verification revalidates the manifest schema and recomputes the digest; mismatches are reported, never repaired automatically.
12. Replay reruns the same versioned synthetic generator from stored scope, batch size, and seed, then compares a semantic fingerprint excluding random record identifiers.

## Failure semantics
- Unknown scope and unauthorized operations fail closed and produce a REJECTED workflow.
- Invalid request shape is rejected by Pydantic/FastAPI before workflow creation.
- Invalid telemetry or evidence manifests fail validation before checkpoint/persistence.
- Transient execution errors are recorded as sanitized error codes; the client may retry or resume within the three-attempt budget.
- Commit failures preserve the EXECUTED checkpoint for retry; the service does not rerun test generation for a commit-only retry.
- Missing run, workflow, or evidence identifiers return 404.
- Evidence verification returns schema validity and the expected/recomputed digest; it does not silently repair mismatches.

## Agent/MoE evolution gates
A model-backed expert must provide: versioned prompt and model identifier; strict input/output schema; bounded tool capabilities; timeout and retry budget; deterministic fallback behavior; adversarial prompt-injection tests; held-out task evaluation; calibration and abstention behavior; traceable provenance. No model output may grant authorization or change security policy.

## Production blockers
Authentication/authorization for multi-user access, a general migration framework, encrypted secret/key management, immutable external evidence storage, distributed workflow engine, observability backend, real independent model agents, operational SLOs, and deployment security review are not yet implemented. Keep the service bound to loopback for local development.
