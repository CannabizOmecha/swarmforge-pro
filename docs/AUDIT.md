# Audit Event Integrity

## Event contract
The local audit ledger records only allowlisted event types and bounded JSON payloads. It excludes raw task payloads, credentials, arbitrary URLs, and telemetry bodies. Events cover workflow acceptance, state transitions, attempt start/failure/exhaustion, rejection, commit, resume requests, and deterministic expert/pipeline outcomes.

## Hash chain
Each row stores a monotonically increasing sequence, unique event ID, event type, subject ID, canonical JSON payload, prior event hash, event hash, and timestamp. The event hash is SHA-256 over all those fields, including the previous hash. The first event uses a 64-zero genesis hash.

SQLite triggers reject UPDATE and DELETE statements against the audit table. GET /audit/verify checks sequence continuity, previous-hash linkage, and each recomputed event hash. GET /audit/events returns a bounded newest-first view.

## Transaction semantics
Workflow state transitions and their audit events are appended in the same SQLite transaction. The final run/finding/evidence bundle, COMMITTED state, and corresponding audit events commit atomically. Expert-task and in-memory pipeline audit events are appended after execution and do not persist task payloads.

## Limitations
This local ledger is tamper-evident, not tamper-proof. A database administrator with filesystem access can drop triggers, rewrite rows, and recompute the hash chain. Hashes are not signed. Production requires an external append-only/WORM store, protected signing keys, access separation, retention policy, backups, and independent monitoring. The audit API is unauthenticated and must remain loopback-only with the current MVP.
