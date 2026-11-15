# AEGIS-MoE Acceptance Matrix

This matrix reflects the implemented local-synthetic MVP only. PASS means a named automated test exists and the current implementation commit passed the linked CI workflow. It does not mean production readiness.

## Latest implementation verification

- Branch: aegis-moe-foundation
- Implementation commit: 705266b30d22f78106fb3430ee2091f5ce34e964
- CI run: [AEGIS CI #19](https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43727042312)
- Result: PASS
- Verified steps: dependency installation, unit/API tests, Python compilation, Ruff lint, and JSON Schema contract validation.
- Previous schema-validation and repository-hygiene commit: 363062da1c6d0467db030738ac70a54dd73e6ee1; [CI #18](https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43726730946) passed.
- Repository tree inspection found no tracked Python bytecode, SQLite database, or generated runtime data at implementation commit 363062d; the later code commit preserves that cleaned tree.
- Historical failure: [CI #7](https://github.com/CannabizOmecha/swarmforge-pro/actions/runs/43662227052) failed at the pytest step. The available GitHub API response exposed the failed step but not its test output, so no exact failing assertion/root cause is asserted. Later CI #18 and #19 passed.

## Acceptance matrix

| Requirement | Test or evidence | Status |
|---|---|---|
| Local synthetic scope only; unknown scopes denied | tests/test_core.py::test_remote_scope_is_not_supported; tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected | PASS |
| Bounded, strict request validation | tests/test_api.py::test_unknown_scope_and_invalid_request_are_rejected | PASS |
| Privacy allowlist and redaction | tests/test_core.py::test_privacy_minimization | PASS |
| Robust MAD baseline behavior | tests/test_core.py::test_mad_and_robust_score | PASS |
| Explicit synthetic security-property assertion | tests/test_core.py::test_synthetic_run_produces_reproducible_evidence | PASS |
| Atomic run/finding/evidence persistence | tests/test_core.py::test_store_bundle_is_atomic_on_constraint_failure | PASS |
| Additive idempotency-table migration | tests/test_core.py::test_store_additive_migration_preserves_existing_tables | PASS |
| Event schema validation and rejection of extra fields | tests/test_validation.py::test_generated_events_and_evidence_meet_versioned_schemas; tests/test_validation.py::test_event_schema_rejects_unapproved_fields | PASS |
| Evidence manifest schema and UUID/scope validation | tests/test_validation.py::test_evidence_schema_rejects_invalid_scope_and_uuid | PASS |
| Evidence SHA-256 verification and tamper detection | tests/test_api.py::test_run_persistence_and_evidence_verification; tests/test_api.py::test_evidence_verification_detects_manifest_tampering | PASS |
| Idempotent request replay and key-conflict rejection | tests/test_api.py::test_idempotency_returns_original_run_and_rejects_key_reuse | PASS |
| Deterministic semantic replay | tests/test_api.py::test_run_replay_reproduces_semantic_fingerprint; tests/test_validation.py::test_same_seed_produces_same_replay_fingerprint; tests/test_validation.py::test_different_seed_changes_replay_fingerprint | PASS |
| Expert routing metadata | tests/test_api.py::test_health_scope_and_agent_routing | PASS as deterministic routing metadata only |
| OPA/Rego authorization runtime parity tests | policy/aegis.rego exists; OPA CLI not integrated in CI | NOT IMPLEMENTED |
| Typed capability-scoped expert adapter runtime | Not implemented | NOT IMPLEMENTED |
| Live LLM/MoE agents | No provider connected or exercised | NOT IMPLEMENTED |
| Durable workflow stage checkpoints and recovery | Current run is sequential/in-process; no Temporal or checkpoint engine | NOT IMPLEMENTED |
| Finding deduplication across runs | Not implemented | NOT IMPLEMENTED |
| Drift, calibration, known-defect and benign-variation benchmarks | Not implemented | NOT IMPLEMENTED |
| OpenTelemetry traces and structured audit backend | Not implemented | NOT IMPLEMENTED |
| API authentication and multi-tenant isolation | Not implemented; bind to loopback only | BLOCKED before any non-loopback exposure |
| General database migrations, key management, immutable external evidence storage | Not implemented | BLOCKED pending deployment/security design |
| Production deployment and operational SLO verification | Not implemented | BLOCKED; no production-readiness claim |

## Release gate

Keep the API bound to 127.0.0.1. Do not expose it on a LAN or public interface until authentication, authorization, secret/key management, external evidence retention, rate limiting, hardened deployment configuration, backup/restore testing, and independent security review are complete. Never enable remote target testing by changing the synthetic scope in code; that requires a separate authorization and threat-model review.
