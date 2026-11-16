# Changelog

## 0.5.0 — durable workflow checkpoints
- Added a SQLite-backed workflow state machine: ACCEPTED, AUTHORIZED, EXECUTED, COMMITTED, REJECTED, and EXHAUSTED.
- Added compare-and-set state transitions and an EXECUTED stage checkpoint.
- Made run, finding, evidence, response-cache, and COMMITTED-state writes atomic.
- Added same-workflow resume after execution or commit failures, including a bounded three-attempt execution budget.
- Added workflow status and resume API endpoints; failed requests return an X-Workflow-ID header for recovery.
- Added tests for execution retry, retry exhaustion, commit-only recovery, state-transition validation, idempotent workflow completion, and compatibility with pre-workflow idempotency records.
- Investigated historical CI #7 from its full job log: the stale API test called the removed Store.save_run method; current coverage exercises transactional bundle persistence.

## 0.4.0 — deterministic replay and schema validation
- Added event/evidence JSON Schema validation.
- Added evidence hash verification and tamper detection.
- Added deterministic synthetic generation and semantic replay fingerprints.
- Added client idempotency keys and atomic run-bundle persistence.
- Added acceptance matrix and orchestration documentation.
