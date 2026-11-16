# AEGIS-MoE Acceptance Matrix

This matrix describes the implemented local-synthetic MVP. PASS means a named automated test exists and the linked GitHub Actions run passed for the referenced implementation commit. It does not mean production readiness.

## Latest implementation verification

- Branch: aegis-moe-foundation
- Implementation commit: 9a5233696c38a96c261e1eb95abd71bfab92d26f
- CI run #26: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43894186350
- Result: PASS.
- Verified job steps: dependency installation, unit/API tests, Python compilation, Ruff lint, and JSON Schema validation all completed successfully.
- Pytest output: 23 tests passed. One upstream Starlette/httpx deprecation warning remains; there were no project pytest-collection warnings.
- Ruff output: All checks passed.
- JSON Schema output: JSON Schema contracts valid.
- Historical CI #7: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43662227052
- Root cause established from the full job log: tests/test_api.py::test_scope_rejection_and_run_persistence called Store.save_run, but the API/store refactor had removed that method. The mismatch raised AttributeError. The test was stale relative to the transactional save_bundle API. This was a test/implementation contract mismatch, not a runtime security finding.
- Repository tree inspection found no tracked Python bytecode, SQLite database, or generated runtime data.

## Acceptance matrix

| Requirement | Test or evidence | Status |
|---|---|---|
| Local synthetic scope only; unknown scopes denied | tests/test_core.py::test_remote_scope_is_not_supported; tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected | PASS |
| Bounded, strict request validation | tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected | PASS |
| Privacy allowlist and redaction | tests/test_core.py::test_privacy_minimization | PASS |
| Robust MAD baseline behavior | tests/test_core.py::test_mad_and_robust_score | PASS |
| Explicit synthetic security-property assertion | tests/test_core.py::test_synthetic_run_produces_reproducible_evidence | PASS |
| Atomic run/finding/evidence persistence | tests/test_core.py::test_store_bundle_is_atomic_on_constraint_failure | PASS |
| Additive SQLite migrations | tests/test_core.py::test_store_additive_migration_preserves_existing_tables | PASS for current additive tables; no general migration framework |
| Event schema validation and rejection of extra fields | tests/test_validation.py::test_generated_events_and_evidence_meet_versioned_schemas; tests/test_validation.py::test_event_schema_rejects_unapproved_fields | PASS |
| Evidence manifest schema and UUID/scope validation | tests/test_validation.py::test_evidence_schema_rejects_invalid_scope_and_uuid | PASS |
| Evidence SHA-256 verification and tamper detection | tests/test_api.py::test_run_persistence_and_evidence_verification; tests/test_api.py::test_evidence_verification_detects_manifest_tampering | PASS |
| Idempotent request replay and key-conflict rejection | tests/test_api.py::test_idempotency_returns_original_run_and_rejects_key_reuse | PASS |
| Deterministic semantic replay | tests/test_api.py::test_run_replay_reproduces_semantic_fingerprint; tests/test_validation.py::test_same_seed_produces_same_replay_fingerprint; tests/test_validation.py::test_different_seed_changes_replay_fingerprint | PASS |
| Durable workflow state transitions and stage checkpoints | tests/test_workflow.py::test_workflow_persists_checkpoints_and_commits_bundle_atomically; tests/test_workflow.py::test_invalid_workflow_transition_is_rejected | PASS |
| Execution failure recovery on the same workflow | tests/test_workflow.py::test_execution_failure_resumes_same_workflow_without_duplicate_run | PASS |
| Bounded retry exhaustion | tests/test_workflow.py::test_workflow_retry_budget_is_bounded | PASS |
| Commit retry resumes from EXECUTED checkpoint without rerunning | tests/test_workflow.py::test_executed_checkpoint_resumes_commit_without_rerunning_engine | PASS |
| Workflow status endpoint | tests/test_api.py::test_run_persistence_and_evidence_verification checks the committed workflow state | PASS |
| Legacy idempotency compatibility across workflow migration | tests/test_workflow.py::test_legacy_idempotency_records_survive_workflow_upgrade | PENDING CI |
| Expert routing metadata | tests/test_api.py::test_health_scope_and_agent_routing | PASS as deterministic routing metadata only |
| OPA/Rego authorization runtime parity tests | policy/aegis.rego exists; OPA CLI not integrated in CI | NOT IMPLEMENTED |
| Typed capability-scoped expert adapter runtime | Not implemented | NOT IMPLEMENTED |
| Live LLM/MoE agents | No provider connected or exercised | NOT IMPLEMENTED |
| Finding deduplication across runs | Not implemented | NOT IMPLEMENTED |
| Drift, calibration, known-defect and benign-variation benchmarks | Not implemented | NOT IMPLEMENTED |
| OpenTelemetry traces and structured audit backend | Not implemented | NOT IMPLEMENTED |
| API authentication and multi-tenant isolation | Not implemented; bind to loopback only | BLOCKED before any non-loopback exposure |
| Encrypted key management and immutable external evidence storage | Not implemented | BLOCKED pending deployment/security design |
| Distributed workflow engine and multi-host recovery | SQLite workflow state is single-node only | NOT IMPLEMENTED |
| Production deployment and operational SLO verification | Not implemented | BLOCKED; no production-readiness claim |

## Release gate

Keep the API bound to 127.0.0.1. Do not expose it on a LAN or public interface until authentication, authorization, secret/key management, external evidence retention, rate limiting, hardened deployment configuration, backup/restore testing, and independent security review are complete. Never enable remote target testing by changing the synthetic scope in code; that requires a separate authorization and threat-model review.
