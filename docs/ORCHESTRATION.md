# AEGIS-MoE Orchestration Contract

## Execution model
The current MVP uses a deterministic, sequential orchestration pipeline. The expert registry is a routing contract, not proof of separately deployed LLM agents. Each stage is explicit so model-backed experts can be introduced behind stable interfaces and independently evaluated.

## Run sequence
1. Governance resolves the immutable local-synthetic scope and operation budget.
2. Test generation creates bounded deterministic fixture cases using a versioned SHA-256-derived synthetic generator.
3. Sandbox stage executes only in-process synthetic fixtures; no network target exists.
4. Privacy stage applies an allowlist before telemetry is persisted.
5. Event schema stage validates every minimized event against the versioned JSON Schema contract.
6. Statistical stage scores observations against a fixed reference distribution.
7. Security validation checks a named property assertion; anomaly scores alone never validate a finding.
8. Evidence stage creates a canonical manifest, validates it against the evidence schema, and computes a SHA-256 digest.
9. Persistence commits the run, findings, evidence, and optional idempotency response in one SQLite transaction.
10. Evidence verification revalidates the manifest schema and recomputes the digest; mismatches are reported, never repaired automatically.
11. Replay reruns the same versioned synthetic generator from stored scope, batch size, and seed, then compares a semantic fingerprint that excludes random record identifiers.

## Idempotency and recovery
- Clients may supply an optional idempotency key (16–128 safe characters).
- The key is bound to a canonical request fingerprint. Repeating the same key and request returns the original response without creating another run.
- Reusing a key with a different request returns HTTP 409.
- The idempotency record is written in the same SQLite transaction as the run bundle. A uniqueness race rolls back the losing bundle; the API then returns the winning response only if its request fingerprint matches.
- The idempotency table is an additive, CREATE TABLE IF NOT EXISTS migration. This MVP has no general migration framework yet.
- Replay checks deterministic semantic equivalence; it does not assert identical UUIDs or timestamps.

## Failure semantics
- Unknown scope and unauthorized operations fail closed.
- Invalid request shape is rejected by Pydantic/FastAPI before execution.
- Invalid telemetry or evidence manifests fail validation before persistence.
- Persistence is atomic: a run must not be stored without its corresponding findings/evidence writes completing.
- Missing run/evidence identifiers return 404.
- Evidence verification returns schema validity and the expected/recomputed digest; it does not silently repair mismatches.

## Agent/MoE evolution gates
A model-backed expert must provide: versioned prompt and model identifier; strict input/output schema; bounded tool capabilities; timeout and retry budget; deterministic fallback behavior; adversarial prompt-injection tests; held-out task evaluation; calibration and abstention behavior; traceable provenance. No model output may grant authorization or change security policy.

## Production blockers
Authentication/authorization for multi-user access, a general migration framework, encrypted secret/key management, immutable external evidence storage, distributed workflow engine, observability backend, real independent model agents, operational SLOs, and deployment security review are not yet implemented. Keep the service bound to loopback for local development.
