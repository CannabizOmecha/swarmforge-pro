# AEGIS-MoE Acceptance Matrix

This matrix reports only evidence that exists in the repository or GitHub Actions. A passing CI run is not equivalent to production readiness.

| Requirement | Evidence | Status |
|---|---|---|
| Local synthetic scope only | `aegis/policy.py`, `test_remote_scope_is_not_supported`, API denial tests | PASS |
| Bounded request validation | `aegis/models.py`, API 422 test | PASS |
| Privacy allowlist and redaction | `aegis/privacy.py`, `test_privacy_minimization` | PASS |
| Robust baseline scoring | `aegis/baseline.py`, `test_mad_and_robust_score` | PASS |
| Explicit security-property fixture validation | `aegis/engine.py`, synthetic run test | PASS |
| Atomic persistence of run/findings/evidence | `aegis/store.py` save_bundle | IMPLEMENTED; CI verification pending |
| Evidence hash generation and verification | `aegis/engine.py`, `GET /evidence/{id}/verify`, API test | IMPLEMENTED; CI verification pending |
| API health/scope/routing/run/findings/metrics | `aegis/api.py`, `tests/test_api.py` | IMPLEMENTED; CI verification pending |
| Versioned event and property schemas | `spec/event.schema.json`, `spec/security_properties.json`, registry JSON | IMPLEMENTED; CI syntax check pending |
| OPA/Rego authorization artifact | `policy/aegis.rego` | ARTIFACT ONLY; OPA runtime tests not yet integrated |
| Deterministic expert routing | `aegis/experts.py` | PASS as routing metadata; not live AI agents |
| Durable distributed workflow orchestration | Not implemented | NOT IMPLEMENTED |
| Real LLM/MoE provider agents | Not integrated or tested | NOT IMPLEMENTED |
| Deterministic replay and finding minimization | Not implemented | NOT IMPLEMENTED |
| Drift/calibration and benchmark evaluation | Not implemented | NOT IMPLEMENTED |
| OpenTelemetry tracing and audit backend | Not implemented | NOT IMPLEMENTED |
| API authentication and multi-tenant isolation | Not implemented; local loopback only | BLOCKED before non-loopback deployment |
| Production deployment, key management, immutable evidence store | Not implemented | BLOCKED pending deployment design/security review |

## CI evidence

- Latest candidate commit: `d30e6d9e92576bb2092f8afae13968ddd3dcbb47`
- Workflow: [AEGIS CI](https://github.com/CannabizOmecha/swarmforge-pro/actions)
- Previous candidate `c6df80b` passed unit/API tests and compilation but failed Ruff lint. The unused import was removed in `d30e6d9`; the new workflow run must finish before this change is marked PASS.

## Release gate

Do not deploy beyond loopback until authentication, deployment configuration, secrets handling, external evidence retention, threat-model review, and recovery tests are implemented and independently verified.
