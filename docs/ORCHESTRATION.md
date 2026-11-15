# AEGIS-MoE Orchestration Contract

## Execution model
The current MVP uses a deterministic, sequential orchestration pipeline. The expert registry is a routing contract, not proof of separately deployed LLM agents. Each stage is explicit so model-backed experts can be introduced behind stable interfaces and independently evaluated.

## Run sequence
1. Governance resolves the immutable local-synthetic scope and operation budget.
2. Test generation creates bounded deterministic fixture cases.
3. Sandbox stage executes only in-process synthetic fixtures; no network target exists.
4. Privacy stage applies an allowlist before telemetry is persisted.
5. Event schema stage validates every minimized event against the versioned JSON Schema contract.
6. Statistical stage scores observations against a fixed reference distribution.
7. Security validation checks a named property assertion; anomaly scores alone never validate a finding.
8. Evidence stage creates a canonical manifest, validates it against the evidence schema, and computes a SHA-256 digest.
9. Persistence commits the run, findings, and evidence in one SQLite transaction.
10. Evidence verification revalidates the manifest schema and recomputes the digest; mismatches are reported, never repaired automatically.

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
Authentication/authorization for multi-user access, migration framework, encrypted secret/key management, immutable external evidence storage, distributed workflow engine, observability backend, real independent model agents, operational SLOs, and deployment security review are not yet implemented. Keep the service bound to loopback for local development.
