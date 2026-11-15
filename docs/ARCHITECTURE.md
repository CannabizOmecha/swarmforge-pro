# Architecture

## Trust boundaries
1. API boundary validates request schemas.
2. Policy boundary resolves scope and operation budgets.
3. Synthetic executor runs deterministic fixtures only.
4. Privacy boundary allowlists telemetry fields before persistence.
5. Detector scores statistical deviation independently of security impact.
6. Security validator confirms only explicit fixture invariant failures.
7. Evidence service hashes canonical manifests.

## MoE routing
The initial implementation exposes deterministic expert contracts and a task router. It does not claim that independent LLM agents are already connected. Future model adapters must be least-privilege, time-bounded, output-schema-validated, and evaluated against held-out tasks.

## Persistence
SQLite is suitable for a single-node MVP. Production multi-worker deployments require a managed relational database, migrations, transaction strategy, access controls, backup/restore tests, and a separate immutable evidence store.

## Extension gates
- External target support requires explicit target authorization, egress proxy allowlists, rate limits, credential isolation, and separate security review.
- Learned anomaly models require benchmarked precision/recall and shadow deployment.
- Autonomous code changes require branch isolation, CI, signed artifacts, rollback, and policy checks.
