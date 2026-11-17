# Architecture

## Trust boundaries
1. API boundary validates request schemas.
2. Policy boundary resolves scope and operation budgets.
3. Synthetic executor runs deterministic fixtures only.
4. Privacy boundary allowlists telemetry fields before persistence.
5. Detector scores statistical deviation independently of security impact.
6. Security validator confirms only explicit fixture invariant failures.
7. Evidence service validates manifests and hashes canonical payloads.
8. Expert runtime routes strict tasks to fixed, least-privilege deterministic adapters.

## Expert runtime
Task type, not caller-supplied expert name, determines routing. The test generator can read fixed synthetic fixtures; the security validator can read fixtures and evaluate the named synthetic invariant; the critic can review candidate structure and candidate digest. The toolbox has no generic external execution methods. Each task has a bounded deadline and input/output byte budgets. Adapter failures abstain; malformed adapter contracts fail closed.

The three-stage validation pipeline is sequential because each stage depends on the prior stage's output. It is an in-memory deterministic demonstration and does not persist findings or evidence. The current adapters are mocks; no live LLM provider is connected.

## Governance policy
The Python application enforces the immutable local-synthetic scope registry at runtime. The Rego policy is versioned, SHA-256 pinned in a manifest, and compiled/tested independently in CI using a pinned OPA CLI binary. OPA is not yet called by the running API; the tests provide policy-contract parity evidence, not a claim of runtime OPA enforcement.

## Persistence
SQLite is suitable for a single-node MVP. Production multi-worker deployments require a managed relational database, general migrations, transaction strategy, access controls, backup/restore tests, and a separate immutable evidence store.

## Extension gates
- External target support requires explicit target authorization, egress proxy allowlists, rate limits, credential isolation, and separate security review.
- Learned anomaly models require benchmarked precision/recall and shadow deployment.
- Model adapters require independent evaluation, token/cost budgets, prompt-injection tests, schema validation, and capability-scoped tools.
- Autonomous code changes require branch isolation, CI, signed artifacts, rollback, and policy checks.
