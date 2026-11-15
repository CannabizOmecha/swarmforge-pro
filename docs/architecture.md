# Architecture and acceptance boundary

## Foundation flow
Intake -> schema validation -> budget check -> risk classification -> task registration -> approval gate -> authorized local execution -> independent artifact evaluation -> evidence record -> append-only event log.

## Separation of duties
- Planner/builder proposes and produces artifacts.
- Governance kernel decides task eligibility.
- Named human approver authorizes high/critical risk and external side effects.
- Local evidence gate checks the evidence contract only; it is not an independent evaluator. Production requires an isolated evaluator and verifiable signed attestations.
- Release authority remains outside the proposing agent.

## Next implementation gates
1. Capability-scoped credentials with expiry, audience, action, resource and budget claims.
2. Temporal workflows for long-running execution.
3. PostgreSQL migrations and concurrency/idempotency tests.
4. OPA/Rego deny-by-default policies.
5. OpenTelemetry traces, metrics and redaction tests.
6. Isolated execution workers, filesystem/network restrictions and resource quotas.
7. Independent adversarial evaluation, replay, crash recovery and rollback.
8. Model adapters and MoE routing only after the above controls pass.

## Current evaluation limitation
The present evidence gate trusts caller-supplied test status and evidence references. It is a schema/contract gate only, not independent test execution, cryptographic attestation, or proof that the referenced artifact is correct. A separate isolated evaluator with signed attestations is a release blocker.

## Release criteria
Unit/integration/security/recovery tests pass; audit verification succeeds; no unapproved side effect is possible; budgets are enforced; result claims link to artifacts; and an independent reviewer approves release.