# AEGIS-MoE

Autonomous, policy-constrained security assurance MVP. It runs deterministic tests against synthetic fixtures, validates privacy-minimized events and evidence manifests against versioned JSON Schemas, scores robust statistical deviations, supports idempotent run submission and deterministic replay, and creates hash-addressed evidence.

## Safety boundary
- Default scope is local-synthetic; no remote target execution is implemented.
- The API does not accept arbitrary URLs, shell commands, credentials, or network destinations.
- Scope authorization is checked before a run.
- A candidate anomaly is not a confirmed vulnerability. Confirmation requires an explicit security-property violation.
- No autonomous policy changes, external disclosure, production deployment, or destructive remediation.

## Quick start
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn aegis.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs.

Run tests:
```bash
pytest -q
ruff check aegis tests
```

## API
- GET /health
- GET /agents
- GET /scope
- GET /routing/{task}
- POST /runs — run a bounded synthetic test batch; optional idempotency_key prevents duplicate submission
- GET /runs/{run_id}
- GET /runs/{run_id}/replay — recompute and compare the deterministic semantic fingerprint
- GET /evidence/{evidence_id}/verify
- GET /findings
- GET /metrics

## Current implementation status
The API, policy, privacy, schema-validation, statistical, evidence, idempotency, replay, and transactional persistence components are implemented for a single-node synthetic MVP. Expert roles are deterministic workers with explicit contracts. This is not a production-grade distributed swarm: live LLM agents, Temporal, NATS, external targets, multi-user authentication, and long-running cloud operation are not integrated or verified.

## Dependency management
pyproject.toml is the single source of dependency constraints. requirements.txt delegates to project metadata to avoid maintaining a second, divergent dependency list. CI installs the project and development extras from that source. A fully hash-locked production dependency set remains a release-hardening task.

## Design principles
Fail closed; minimize data at collection; validate persisted contracts; separate anomaly scoring from security validation; preserve content-addressed evidence; version policies and test definitions; never learn away a security invariant.
