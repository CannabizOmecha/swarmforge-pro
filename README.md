# AEGIS-MoE

Autonomous, policy-constrained security assurance MVP. This implementation is deliberately local-first: it runs deterministic tests against synthetic fixtures, validates explicit security properties, records privacy-minimized telemetry, scores robust statistical deviations, and creates hash-addressed evidence.

## Safety boundary
- Default scope is `local-synthetic`; no remote target execution is implemented.
- The API does not accept arbitrary URLs, shell commands, credentials, or network destinations.
- Scope authorization is checked before a run.
- A candidate anomaly is not a confirmed vulnerability. Confirmation requires an explicit security-property violation.
- No autonomous policy changes, external disclosure, production deployment, or destructive remediation.

## Quick start
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
uvicorn aegis.api:app --reload
```

Open `http://127.0.0.1:8000/docs`.

Run tests:
```bash
pytest -q
```

## Current implementation status
This is a functioning foundation, not a claim of a production-grade multi-model swarm. Expert roles are deterministic workers with explicit contracts. LLM adapters, distributed execution, Temporal, NATS, OPA deployment, external targets, and long-running cloud operation remain extension points requiring separate integration and evaluation.

## API
- `GET /health`
- `GET /agents`
- `GET /scope`
- `POST /runs` — run a bounded synthetic test batch
- `GET /runs/{run_id}`
- `GET /findings`
- `GET /metrics`

## Design principles
Fail closed; minimize data at collection; separate anomaly scoring from security validation; preserve immutable-by-content evidence; version policies and test definitions; never learn away a security invariant.
