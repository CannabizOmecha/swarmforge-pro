# AEGIS-MoE Acceptance Matrix

This matrix reports the local-synthetic implementation only. PASS means a named automated test exists and the referenced GitHub Actions job completed successfully for the implementation commit. It is not a production-readiness claim.

## Latest implementation verification

- Branch: `aegis-moe-foundation`
- Latest verified implementation commit: `2c4429a0c055b2794636b1af773ff307e87c0e3f`
- CI run #42: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44138390159 — PASS, final acceptance/orchestration documentation verification.
- CI run #41: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44138196351
- Result: PASS.
- Pytest: `50 passed, 1 warning in 0.85s`; the warning is an upstream Starlette/httpx TestClient deprecation.
- Ruff: `All checks passed!`
- JSON Schema: `JSON Schema contracts valid`
- Policy manifest: verified policy version 1.0.0 and SHA-256 `50a42b6d44bd45eb53285c846cd388e9693b146611f1fabbcc63afc4c9204759`.
- OPA CLI: pinned 1.22.4 binary digest verified; Rego format and compilation checks passed; Rego tests: `9/9`.
- CI run #38: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44137351212 — PASS, initial OPA integration, 8/8 Rego tests.
- CI run #35: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44136717247 — PASS, 42 Python tests.
- CI run #34: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44136561622 — PASS, 42 Python tests.
- CI run #33: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44136166329 — PASS, deterministic three-expert pipeline.
- CI run #32: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135889614 — PASS, first typed runtime increment.
- CI run #31: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135757865 — FAIL, pytest passed but Ruff flagged a broad exception boundary and import ordering; corrected.
- CI run #30: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44135594423 — FAIL, critic capability-use regression; corrected through the scoped toolbox.
- CI run #39: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44138000752 — FAIL, Ruff import-source rule; corrected.
- CI run #40: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44138099718 — FAIL, Ruff import ordering; corrected.
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
| Immutable Python scope registry and startup validation | tests/test_policy.py registry immutability and invalid-registry tests | PASS |
| Versioned Rego policy and SHA-256 manifest verification | scripts/verify_policy_manifest.py; CI #41 | PASS |
| OPA/Rego positive and negative policy tests | CI #41 OPA 1.22.4: format, compile, and 9/9 Rego tests; matching Python policy tests | PASS for independently tested policy artifact |
| OPA invoked by the running API | Not implemented; Python remains runtime authorization layer | NOT IMPLEMENTED |
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
