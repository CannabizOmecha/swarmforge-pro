# Changelog

## 0.4.0 — 2026-11-15
- Replaced runtime pseudo-random latency generation with a versioned SHA-256-derived deterministic synthetic generator.
- Added semantic replay fingerprints and GET /runs/{run_id}/replay.
- Added optional idempotency keys bound to canonical request fingerprints.
- Persisted idempotency responses in the same SQLite transaction as run/finding/evidence records.
- Added HTTP 409 handling for conflicting idempotency-key reuse.
- Added an additive SQLite migration for the idempotency table.
- Added tests for same-key replay, conflicting requests, deterministic fingerprints, and migration behavior.

## 0.3.0 — 2026-11-15
- Added runtime JSON Schema validation for minimized events and evidence manifests.
- Made evidence verification check both schema validity and recomputed SHA-256 digest.
- Added regression tests for schema rejection, tampered evidence, and atomic persistence rollback.
- Removed tracked Python bytecode and expanded runtime artifact ignores.
- Centralized dependency constraints in pyproject.toml; requirements.txt now delegates to project metadata.
- Expanded CI to validate schema contracts after tests, compilation, and lint.

## 0.2.0 — 2026-11-15
- Added API integration tests, atomic persistence, evidence retrieval and verification, routing metadata, and orchestration documentation.

## 0.1.0 — 2026-11-15
- Established local-synthetic-only FastAPI MVP with scope enforcement, privacy minimization, robust baseline scoring, deterministic fixture validation, and SHA-256 evidence manifests.
