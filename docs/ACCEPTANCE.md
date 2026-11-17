# AEGIS-MoE Acceptance Matrix

This matrix reports the local-synthetic implementation only. PASS means a named automated test exists and the referenced GitHub Actions job completed successfully for the implementation commit. It is not a production-readiness claim.

## Latest implementation verification

- Branch: `aegis-moe-foundation`
- Latest full-branch verification commit: `5514e2985f98fdeed8bb0705f2714ff158370da0`
- CI run #34: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44136561622
- Result: PASS.
- Verified job steps: dependency installation, unit/API tests, Python compilation, Ruff lint, and JSON Schema validation all completed successfully.
- Pytest: `42 passed, 1 warning in 0.83s`. The warning is an upstream Starlette/httpx TestClient deprecation; no project test failed.
- Ruff: `All checks passed!`
- JSON Schema: `JSON Schema contracts valid`
- Expert runtime implementation commit: `673b16d5375f022ddea4c240d173da3bf010a72b`
- CI run #33: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44136166329 — PASS for the three-stage deterministic expert pipeline.
- Workflow CI #32: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135889614 — PASS for the first typed runtime increment.
- Workflow CI #31: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135757865 — FAIL, pytest passed but Ruff flagged a broad exception boundary and import ordering. Both were corrected.
- Workflow CI #30: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135594423 — FAIL, one test showed that the critic's review capability was not recorded by the toolbox. The review operation was moved behind the capability-checked toolbox method and regression-tested.
- Earlier workflow CI #29: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43894779810 — PASS for the durable workflow baseline.
- Historical CI #7 root cause was a stale test calling the removed Store.save_run method after the transactional save_bundle refactor; this was a test/implementation contract mismatch, not a security finding.

## Acceptance matrix

| Requirement | Test or evidence | Status |
|---|---|---|
| Local synthetic scope only; unknown run scopes denied | `tests/test_core.py::test_remote_scope_is_not_supported`; `tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected` | PASS |
| Strict, bounded run request validation | `tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected` | PASS |
| Privacy allowlist and redaction | `tests/test_core.py::test_privacy_minimization` | PASS |
| Robust MAD baseline behavior | `tests/test_core.py::test_mad_and_robust_score` | PASS |
| Explicit synthetic security-property assertion | `tests/test_core.py::test_synthetic_run_produces_reproducible_evidence` | PASS |
| Atomic run/finding/evidence persistence | `tests/test_core.py::test_store_bundle_is_atomic_on_constraint_failure` | PASS |
| Additive SQLite migration compatibility | `tests/test_core.py::test_store_additive_migration_preserves_existing_tables` | PASS for current additive tables; no general migration framework |
| Event/evidence schema validation | `tests/test_validation.py` schema contract tests | PASS |
| Evidence SHA-256 verification and tamper detection | `tests/test_api.py::test_run_persistence_and_evidence_verification`; `test_evidence_verification_detects_manifest_tampering` | PASS |
| Idempotent submission and key conflict rejection | `tests/test_api.py::test_idempotency_returns_original_run_and_rejects_key_reuse` | PASS |
| Deterministic semantic replay | `tests/test_api.py::test_run_replay_reproduces_semantic_fingerprint`; `tests/test_validation.py` replay fingerprint tests | PASS |
| Durable workflow transitions, checkpoints, recovery, retry exhaustion | `tests/test_workflow.py` workflow recovery tests | PASS |
| Legacy idempotency compatibility | `tests/test_workflow.py::test_legacy_idempotency_records_survive_workflow_upgrade` | PASS |
| Strict typed expert task and result contracts | `tests/test_agents.py` strict payload/deadline tests | PASS |
| Static task-to-expert routing; caller cannot self-select expert | `tests/test_agents.py::test_task_routes_to_fixed_least_privilege_expert`; `tests/test_api.py` agent endpoint tests | PASS |
| Capability-scoped read-only synthetic toolbox | `tests/test_agents.py::test_toolbox_denies_ungranted_capability` | PASS |
| Per-task deadline and bounded input/output | `tests/test_agents.py::test_deadline_causes_abstention_not_unbounded_execution`; `test_adapter_output_budget_is_enforced` | PASS |
| Adapter failure abstention and sanitized reason | `tests/test_agents.py::test_adapter_failure_abstains_without_exposing_exception_text` | PASS |
| Independent validator and critic roles | `tests/test_agents.py::test_validator_is_separate_and_confirms_only_explicit_fixture_violation`; three-stage pipeline tests | PASS |
| Candidate digest integrity and tamper detection | `tests/test_agents.py::test_critic_rejects_candidate_digest_tampering` | PASS |
| Sequential three-expert orchestration and stop-on-abstain | `tests/test_agents.py` pipeline tests; `tests/test_api.py::test_agent_pipeline_endpoint_runs_three_independent_experts` | PASS |
| Live LLM/MoE provider agents | No provider connected or exercised | NOT IMPLEMENTED |
| Provider token/cost budgets and model calibration | No live provider; no model evaluation set | NOT IMPLEMENTED |
| OPA/Rego runtime parity tests | Rego policy exists; OPA CLI not integrated in CI | NOT IMPLEMENTED |
| Cross-run finding deduplication | Not implemented | NOT IMPLEMENTED |
| Drift/calibration/known-defect/benign-variation benchmarks | Not implemented | NOT IMPLEMENTED |
| OpenTelemetry traces and structured audit backend | Not implemented | NOT IMPLEMENTED |
| General-purpose migration framework | Additive SQLite migrations only | NOT IMPLEMENTED |
| Distributed workflow engine and multi-host recovery | SQLite workflow state is single-node only | NOT IMPLEMENTED |
| API authentication and multi-tenant isolation | Not implemented; loopback binding required | BLOCKED before any non-loopback exposure |
| Encrypted key management and immutable external evidence storage | Not implemented | BLOCKED pending deployment/security design |
| Production deployment and operational SLO verification | Not implemented | BLOCKED; no production-readiness claim |

## Release gate

Keep the API bound to `127.0.0.1`. Do not expose it on a LAN or public interface until authentication, authorization, secret/key management, external evidence retention, rate limiting, hardened deployment configuration, backup/restore testing, and independent security review are complete. Never enable remote target testing by changing the synthetic scope in code; that requires a separate authorization and threat-model review.
