# AEGIS-MoE Acceptance Matrix

This matrix reports the local-synthetic implementation only. PASS means a named automated test exists and the referenced GitHub Actions job completed successfully for the implementation commit. It is not a production-readiness claim.

## Latest implementation verification

- Branch: `aegis-moe-foundation`
- Latest verified implementation commit: `d7f1dc6a5ef037cdb456a665a99af9197f695945`
- CI run #75: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/45049353434
- Result: PASS; exact head SHA checked. Pytest `88 passed, 1 warning`; compileall, Ruff, JSON Schema, immutable policy manifest, pinned OPA installation, Rego format/check, and OPA tests all passed (9/9).
- Reliability counters: bounded fixed-cardinality retry, abstention, workflow-stage failure, and recovery outcome counters. Tests cover retry scheduling, retry exhaustion, recovery completion/exhaustion, and exclusion of workflow identifiers and private exception text.
- Workflow-stage tracing: fixed stage/outcome registries and sanitized bounded exporter.
- Repository governance: PR template and contribution rules added. GitHub branch protection is **not yet active**; see `docs/BRANCH_PROTECTION.md` for the required administrator configuration and verification procedure.
- CI run #72: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/45048297480 — PASS, initial reliability-metrics implementation.
- CI run #74: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/45048435400 — PASS, verified reliability metrics documentation and changelog.
- Historical CI #7 root cause: stale test called the removed Store.save_run method after the transactional save_bundle refactor; this was a test/implementation contract mismatch, not a security finding.

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
| Cross-run finding grouping with case-sensitive semantic fingerprints; all original findings/evidence retained | `tests/test_core.py::test_finding_fingerprint_ignores_run_specific_identifiers`; `tests/test_api.py::test_cross_run_finding_dedup_preserves_occurrences_and_groups`; `test_finding_group_listing_limit_is_bounded` | PASS |
| Historical finding-group backfill | `tests/test_backfill.py::test_backfill_reconciles_historical_findings_and_is_idempotent`; `test_backfill_aborts_without_partial_changes_on_malformed_source`; `test_backfill_rejects_mismatched_storage_and_payload_ids` | PASS (CI #55) |
| Live LLM/MoE provider agents | No provider connected or exercised | NOT IMPLEMENTED |
| Provider token/cost budgets and model calibration | No live provider; no model evaluation set | NOT IMPLEMENTED |
| Immutable Python scope registry and startup validation | tests/test_policy.py registry immutability and invalid-registry tests | PASS |
| Append-only hash-chained audit log and tamper detection | tests/test_core.py audit append-only/tamper tests; tests/test_workflow.py workflow event test; tests/test_api.py audit endpoints | PASS |
| Versioned Rego policy and SHA-256 manifest verification | scripts/verify_policy_manifest.py; CI #41 | PASS |
| OPA/Rego positive and negative policy tests | CI #41 OPA 1.22.4: format, compile, and 9/9 Rego tests; matching Python policy tests | PASS for independently tested policy artifact |
| OPA invoked by the running API | Not implemented; Python remains runtime authorization layer | NOT IMPLEMENTED |
| Cross-run finding deduplication | Versioned semantic fingerprints; transactional occurrence grouping; regression tests preserve case-sensitive semantics and retain original findings/evidence | PASS (CI #46–#48) |
| Offline robust-anomaly benchmark (known statistical anomalies, benign variation, zero-MAD, no-baseline abstention) | `tests/test_benchmark.py` | PASS (CI #52) |
| Bounded local OpenTelemetry HTTP traces with strict attribute allowlist and sensitive-data regression tests | `tests/test_observability.py`; `tests/test_api.py::test_http_spans_exclude_query_headers_and_request_values`; `test_telemetry_spans_endpoint_enforces_bounded_limit` | PASS (CI #58) |
| Workflow-stage spans use fixed stage/outcome registries and preserve telemetry privacy | `tests/test_observability.py::test_workflow_stage_trace_uses_registered_stage_and_outcome_only`; `test_workflow_stage_rejects_unregistered_stage_names`; CI #68 implementation PASS and #69 final documentation PASS | PASS |
| Remote trace collector/exporter and durable telemetry backend | Not configured; no network telemetry path | NOT IMPLEMENTED |
| General-purpose migration framework | Additive SQLite migrations only | NOT IMPLEMENTED |
| Distributed workflow engine and multi-host recovery | SQLite workflow state is single-node only | NOT IMPLEMENTED |
| API authentication and multi-tenant isolation | Not implemented; loopback binding required | BLOCKED before any non-loopback exposure |
| Encrypted key management and immutable external evidence storage | Not implemented | BLOCKED pending deployment/security design |
| Production deployment and operational SLO verification | Not implemented | BLOCKED; no production-readiness claim |

## Release gate

Keep the API bound to `127.0.0.1`. Do not expose it on a LAN or public interface until authentication, authorization, secret/key management, external evidence retention, rate limiting, hardened deployment configuration, backup/restore testing, and independent security review are complete. Never enable remote target testing by changing the synthetic scope in code; that requires a separate authorization and threat-model review.


## Offline anomaly benchmark increment

- Implementation commit: pending CI verification.
- Benchmark contract: `aegis/benchmark.py`; tests: `tests/test_benchmark.py`; documentation: `docs/ANOMALY_BENCHMARK.md`.
- Labels distinguish statistical anomalies from explicit security-property violations; missing baselines abstain and are excluded from metrics.
- Threshold sensitivity is tested (2.5 versus 3.5), along with zero-dispersion behavior, metric edge cases, duplicate IDs, and non-finite inputs.
- CI run #51: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44356991496 — FAIL; pytest passed (72 tests) but Ruff rejected import ordering and deprecated `typing.Iterable`; corrected in commit below.

## Historical finding-group reconciliation increment

- Implementation: `aegis/backfill.py`; CLI: `python -m aegis.backfill --database data/aegis.sqlite3` (dry-run by default).
- Apply only after reviewing the dry-run: `python -m aegis.backfill --database data/aegis.sqlite3 --apply`.
- Source of truth: every persisted finding row, validated through the strict Pydantic Finding model. The finding-group table is treated as a rebuildable derived index.
- Apply mode takes a SQLite `BEGIN IMMEDIATE` lock, validates and aggregates all source rows before replacing the index, and commits the rebuilt index and audit event atomically.
- Repeated apply is a no-op when the derived index already matches source findings. Invalid or mismatched source records abort the transaction.
- Regression tests: `tests/test_backfill.py`.
- Implementation commit: `8537d365be3cf09bcad304712907fa1568e68daf`; lint correction: `bbc3683555891033250bba72899903a5f018c96b`.
- CI run #54: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44549492229 — FAIL at Ruff; pytest and compilation steps passed. Import organization was corrected before the next run; detailed Ruff diagnostics were not available in the job summary.
- CI run #55: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44549671788 — PASS; pytest, compileall, Ruff, JSON Schema, policy manifest, and OPA/Rego steps all succeeded.

## Privacy-safe observability increment

- Implementation: `aegis/observability.py`; middleware and bounded read-only diagnostics: `aegis/api.py`; regression tests: `tests/test_observability.py` and `tests/test_api.py`; design: `docs/OBSERVABILITY.md`.
- Exporter is in-memory only, capped at 256 sanitized span snapshots; no raw SDK spans are retained.
- Only fixed HTTP methods, registered route templates, integer status codes, static service version, and duration are retained. Query strings, headers, bodies, client addresses, exception details, events, links, and unknown attributes are excluded.
- Implementation commit: `dbfbb44640bdda0bfe1b6a150d3100fd43b87063`; Ruff import-order correction: `6b6de3746c8b44bc16c0dc34bb95cb5e69334871`.
- CI run #57: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44758195256 — FAIL at Ruff import ordering in the new observability module and test module; all 81 tests and compilation passed. Corrected in `6b6de3746c8b44bc16c0dc34bb95cb5e69334871`.
- CI run #58: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44758328611 — PASS on the corrected implementation commit; 81 tests passed, compileall passed, Ruff passed, JSON Schema passed, policy manifest passed, and OPA/Rego tests passed 9/9.


## Workflow-stage tracing increment (2026-11-21)

- Implementation: `workflow_stage` helper in `aegis/observability.py`; orchestration instrumentation in `aegis/workflow.py` for authorize, execute, checkpoint, commit, and resume.
- Finite stage and outcome allowlists prevent caller-controlled trace cardinality. Exporter remains in-memory, sanitized, bounded, and network-free.
- Regression tests: `tests/test_observability.py::test_workflow_stage_trace_uses_registered_stage_and_outcome_only`; `test_workflow_stage_rejects_unregistered_stage_names`.
- CI run #65: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44916223520 — FAIL at Ruff I001 import ordering; pytest `83 passed, 1 warning`, compileall passed. Exact Ruff diagnostic fetched: reorder `collections` imports before `contextlib`. Corrected in the next commit.
- CI run #68: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44916287286 — PASS on implementation/changelog SHA `629fb03af6de6d94cb8e4c316d739810edc2fd5b` (2026-11-21). Exact logs: `83 passed, 1 warning in 1.33s`; compileall passed; Ruff `All checks passed!`; JSON Schema `JSON Schema contracts valid`; immutable policy manifest verified; OPA/Rego `PASS: 9/9`. The single warning is the existing Starlette/httpx TestClient deprecation.


## Workflow-stage tracing final verification (2026-11-21)

- Final branch head inspected on 2026-11-22: `b107278bd0d1ab7a9206c105cd54aca37e2677d8`; recent commits are workflow tracing implementation, lint correction, and verification documentation.
- Final CI run #69: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/44916331577 — completed successfully. Job ID `136882620175`; all reported steps succeeded, including tests, compile, Ruff, schema, manifest, and OPA/Rego 9/9.
- The previous matrix was stale (it named CI #58 and omitted stage-level tracing); this update corrects the top-level verified SHA/run and explicitly adds the workflow-stage criterion.
- No source code changed in this acceptance-matrix refresh. CI will verify the documentation-only commit itself.


## Workflow reliability metrics increment (2026-11-22)

- Implementation: `BoundedReliabilityCounters` in `aegis/observability.py`; instrumentation in `aegis/workflow.py` and `aegis/agent_runtime.py`; JSON diagnostics in `GET /metrics`.
- Four fixed counter families: retry scheduling/exhaustion, expert abstention reason, registered stage failures, and recovery outcome. Labels are closed enums; unknown labels are rejected and counts saturate at 63-bit maximum.
- Process-local, non-durable counters only; no identifiers, exception text, request content, or agent output; no network exporter.
- Tests: `tests/test_observability.py::test_reliability_counter_registry_is_fixed_cardinality_and_saturating`; `tests/test_workflow.py::test_retry_and_recovery_outcomes_are_counted_without_identifiers`; `tests/test_agents.py::test_abstention_metrics_use_only_registered_reason_labels`; `tests/test_api.py::test_metrics_endpoint_exposes_bounded_reliability_counters`.
- Status: PASS on implementation SHA `946b6f264acec53b7959a646d1f98a01773d2639`, CI #72 above. Retry and stage-failure increments are exercised by the transient execution-failure recovery test; deadline abstention and the `/metrics` bounded schema are tested.
- CI #71: https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/45048238203 — FAIL at Ruff I001 import ordering in `aegis/api.py`; pytest `87 passed` and compileall passed. Corrected import order in commit `946b6f264acec53b7959a646d1f98a01773d2639`; CI #72 passed.
