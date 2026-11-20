# AEGIS-MoE

Autonomous, policy-constrained security assurance MVP. It runs deterministic tests against synthetic fixtures, validates privacy-minimized events and evidence manifests against versioned JSON Schemas, scores robust statistical deviations, supports idempotent run submission and deterministic replay, and provides a typed, least-privilege deterministic expert runtime.

## Safety boundary
- Default scope is local-synthetic; no remote target execution is implemented.
- The API does not accept arbitrary URLs, shell commands, credentials, or network destinations.
- Expert tools expose only fixed, read-only synthetic fixture operations.
- Scope authorization is checked before a workflow or expert task; the Python scope registry is immutable and validated at startup.
- Rego policy is versioned and SHA-256 pinned; CI verifies its manifest and runs OPA format, compile, and positive/negative tests.
- A candidate anomaly is not a confirmed vulnerability. Confirmation requires an explicit security-property violation.
- The expert runtime currently uses deterministic mock adapters, not live LLM providers.
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
- GET /agents — expert registry and capability metadata
- GET /scope
- GET /routing/{task}
- POST /agent-tasks — execute one strict, bounded expert task
- POST /agent-pipelines/validate — run test_generator → security_validator → critic against a synthetic fixture
- POST /runs — run a bounded synthetic test batch; optional idempotency_key prevents duplicate submission and resumes the same workflow
- GET /workflows/{workflow_id} — inspect state and bounded execution-attempt count
- POST /workflows/{workflow_id}/resume — resume a persisted workflow from its last durable checkpoint
- GET /runs/{run_id}
- GET /runs/{run_id}/replay — recompute and compare the deterministic semantic fingerprint
- GET /evidence/{evidence_id}/verify
- GET /findings
- GET /metrics
- GET /telemetry/spans?limit=20 — bounded, privacy-filtered in-memory OpenTelemetry snapshots
- GET /audit/events?limit=100 — list bounded sanitized audit events
- GET /audit/verify — verify the local append-only audit hash chain

The expert pipeline is an in-memory demonstration and does not create persisted findings or evidence. The normal synthetic run workflow remains the persisted evidence-producing path.

A transient run failure returns HTTP 503 and an X-Workflow-ID response header. Retry POST /runs with the same idempotency key, or call the resume endpoint with that workflow ID. Execution is capped at three attempts. The final run/finding/evidence bundle and COMMITTED workflow state are written atomically.

## Current implementation status
The local-synthetic API, policy boundary, privacy filtering, schema validation, statistical scoring, evidence verification, idempotency, deterministic replay, transactional workflow recovery, deterministic expert runtime, and bounded privacy-filtered local OpenTelemetry tracing are implemented and tested. The expert runtime has typed task/result contracts, statically assigned least-privilege capabilities, a read-only fixture toolbox, per-stage deadlines, input/output size budgets, abstention behavior, and a separate critic stage.

This is not a production-grade distributed swarm. Live LLM agents, model-provider adapters, Temporal, NATS, external targets, multi-user authentication, and long-running cloud operation are not integrated or verified.

## Privacy-safe observability

HTTP requests are traced with OpenTelemetry using a bounded in-memory exporter. Only allowlisted method, route-template, response-status, static service-version, and duration metadata are retained. Query strings, headers, bodies, client addresses, exception details, span events, and links are excluded. See [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md). No trace data is sent over the network.

## Dependency management
pyproject.toml is the single source of dependency constraints. requirements.txt delegates to project metadata to avoid maintaining a second, divergent dependency list. CI installs the project and development extras from that source. A fully hash-locked production dependency set remains a release-hardening task.

## Design principles
Fail closed; minimize data at collection; validate persisted contracts; separate anomaly scoring from security validation; preserve content-addressed evidence; version policies and test definitions; never learn away a security invariant.

## Offline anomaly benchmark

The deterministic synthetic benchmark is available without API or network access:

```python
from aegis.benchmark import DEFAULT_CASES, evaluate_benchmark

report = evaluate_benchmark(DEFAULT_CASES, threshold=3.5)
print(report.metrics)
```

It evaluates statistical anomaly scoring against labeled synthetic latency cases and reports precision, recall, false-positive rate, and accuracy. A statistical anomaly is not a security finding; explicit security-property validation remains a separate gate. The benchmark is a smoke/calibration fixture, not a statistically representative production dataset.
