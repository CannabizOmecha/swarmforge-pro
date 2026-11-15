# Threat Model

## Assets
Authorization scope, synthetic fixtures, security-property definitions, telemetry, findings, evidence manifests, workflow state.

## Threats
- Scope expansion or confused-deputy behavior.
- Prompt injection through untrusted telemetry.
- Sensitive-data leakage.
- False-positive escalation.
- Baseline poisoning.
- Evidence tampering.
- Resource exhaustion.
- Compromised dependency or agent output.

## Controls
- Static scope registry and fail-closed policy checks.
- No arbitrary URL, shell, or credential inputs.
- Allowlist-first telemetry minimization.
- Separate anomaly scoring and invariant validation.
- Frozen reference baseline for the synthetic MVP.
- Canonical evidence hashing.
- Bounded batch size and local-only execution.
- Deterministic workers; future model outputs must be treated as untrusted data.

## Residual risks
This MVP is not a hardened production deployment. SQLite access control, API authentication, multi-tenant isolation, key management, immutable storage, and external-target controls are not implemented.
