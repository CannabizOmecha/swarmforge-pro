# Changelog

## Unreleased — durable workflow checkpoints
- Added a SQLite-backed workflow state machine: ACCEPTED, AUTHORIZED, EXECUTED, COMMITTED, REJECTED, and EXHAUSTED.
- Added compare-and-set state transitions and an EXECUTED stage checkpoint.
- Made run, finding, evidence, response-cache, and COMMITTED-state writes atomic.
- Added same-workflow resume after execution or commit failures, including bounded three-attempt execution.
- Added workflow status and resume API endpoints.
- Investigated historical CI #7 from its full job log: the stale API test called the removed Store.save_run method; updated coverage now exercises the current transactional API.

## 0.4.0 — deterministic replay and schema validation
- Added event/evidence JSON Schema validation.
- Added evidence hash verification and tamper detection.
- Added deterministic synthetic generation and semantic replay fingerprints.
- Added client idempotency keys and atomic run-bundle persistence.
- Added acceptance matrix and orchestration documentation.
