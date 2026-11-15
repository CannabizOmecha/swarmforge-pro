# ASYA Foundation 0.1.0

A local-first governance and independent-evaluation kernel for multi-agent work. This branch is a foundation scaffold, not a deployed autonomous swarm.

## Safety and scope
- Task proposals are separated from approvals.
- High/critical-risk tasks and external side effects require explicit human authorization.
- Completion requires acceptance criteria, a passing test signal, and an evidence reference.
- SQLite stores task state and a SHA-256 hash-linked event log.
- The executor accepts local artifact metadata only. It does not execute arbitrary code, call external services, publish, spend money, or deploy infrastructure.
- Hash chaining is tamper-evidence, not protection against a privileged attacker rewriting the database and all hashes.

## Local verification
Run `python -m unittest discover -s tests -v` from the exported project folder.

## Not yet complete
Temporal durability, PostgreSQL migrations, OPA/Rego, capability-token enforcement, OpenTelemetry, external model adapters, sandboxed execution, deployment hardening and live MoE routing remain explicit future gates. No production-readiness claim is made.