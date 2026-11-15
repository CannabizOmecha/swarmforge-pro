# AEGIS-MoE Orchestration Contract

## Execution model
The current MVP uses a deterministic, sequential orchestration pipeline. The expert registry is a routing contract, not proof of separately deployed LLM agents. Each stage is explicit so model-backed experts can be introduced behind stable interfaces and independently evaluated.

## Run sequence
1. Governance resolves the immutable local-synthetic scope and operation budget.
2. Test generation creates bounded deterministic fixture cases.
3. Sandbox stage executes only in-process synthetic fixtures; no network target exists.
4. Privacy stage applies an allowlist before telemetry is persisted.
5. Statistical stage scores observations against a fixed reference distribution.
6. Security validation checks a named property assertion; anomaly scores alone never validate a finding.
7. Evidence stage creates a canonical manifest and SHA-256 digest.
8. Persistence commits the run, findings, and evidence in one SQLite transaction.
9. Quality endpoints expose run and finding counts; evidence has an independent verification endpoint.

## Failure semantics
- Unknown scope and unauthorized operations fail closed.
- Invalid request shape is rejected by Pydantic/FastAPI before execution.
- Persistence is atomic: a run must not be stored without its corresponding findings/evidence writes completing.
- Missing run/evidence identifiers return 404.
- Evidence verification returns the expected and recomputed digest and does not silently repair mismatches.

## Agent/MoE evolution gates
A model-backed expert must provide: versioned prompt and model identifier; strict input/output schema; bounded tool capabilities; timeout and retry budget; deterministic fallback behavior; adversarial prompt-injection tests; held-out task evaluation; calibration and abstention behavior; traceable provenance. No model output may grant authorization or change security policy.

## Production blockers
Authentication/authorization for multi-user access, migration framework, encrypted secret/key management, immutable external evidence storage, distributed workflow engine, observability backend, real independent model agents, operational SLOs, and deployment security review are not yet implemented. Keep the service bound to loopback for local development.
