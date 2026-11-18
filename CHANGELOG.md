# Changelog

## 0.6.4 — offline anomaly benchmark (CI #52 passed)
- Added a versioned synthetic benchmark for robust anomaly scoring with nominal cases, benign variation, statistical outliers, zero-dispersion behavior, and missing-baseline abstention.
- Reports confusion counts, precision, recall, false-positive rate, and accuracy at a configurable threshold.
- Keeps statistical anomalies separate from explicit security-property violations; the benchmark does not claim vulnerability-detection performance.
- Added threshold sensitivity, input validation, and metric edge-case tests.


## 0.6.3 — cross-run finding deduplication
- Added versioned semantic finding fingerprints over property, state, impact, expected behavior, and observed behavior.
- Added transactional finding-group aggregation with first/last-seen metadata and occurrence counts.
- Preserved every original finding and its evidence; deduplication is an index/roll-up, not deletion or evidence merging.
- Added a bounded finding-group API and aggregate metric.
- Added tests proving run-specific IDs do not prevent deduplication and distinct occurrences/evidence remain available.


## 0.6.2 — local audit integrity
- Added append-only SQLite audit events with update/delete guards and a SHA-256 hash chain.
- Recorded workflow acceptance, transitions, attempts, execution failures, rejection, commit, resume requests, and agent/pipeline outcomes.
- Added bounded audit listing and chain verification endpoints.
- Added regression tests for append-only enforcement, tamper detection, workflow event coverage, and API audit records.
- Documented that the local hash chain is not a signed/WORM audit store and is not tamper-proof against a privileged database administrator.


## 0.6.1 — policy integrity and OPA parity
- Added a versioned Rego policy and a SHA-256 policy manifest verified by CI.
- Pinned OPA CLI 1.22.4 by the official release asset digest; CI runs Rego formatting, compilation, and positive/negative policy tests.
- Made the Python scope registry immutable and added validation against the fixed local-synthetic policy envelope.
- Added matching Python authorization regression tests; Python remains runtime enforcement while OPA is independently compiled and tested in CI.


## 0.6.0 — typed expert runtime and deterministic MoE pipeline
- Added strict task, payload, adapter-response, and result contracts.
- Added static task-to-expert routing so API callers cannot select a privileged expert or self-assign capabilities.
- Added read-only synthetic fixture tools and explicit per-expert capability grants.
- Added bounded per-task deadlines, input/output byte budgets, result-schema validation, and fail-closed adapter abstention.
- Added separate test-generator, security-validator, and critic stages with candidate digest integrity checks.
- Added POST /agent-tasks and POST /agent-pipelines/validate endpoints.
- Added tests for capability denial, payload rejection, deadlines, output budgets, adapter abstention, critic integrity, pipeline ordering, and early stop when the validator abstains.
- Clarified that the expert pipeline is deterministic and in-memory; it does not persist findings or evidence and does not represent live LLM agents.
- Removed duplicate pytest quiet configuration so CI displays the exact test summary.

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
