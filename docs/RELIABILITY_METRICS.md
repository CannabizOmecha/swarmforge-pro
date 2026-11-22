# Workflow Reliability Metrics

The local `GET /metrics` response exposes aggregate counters under `workflow_reliability`. These counters are process-local and deliberately use a fixed-cardinality registry. Labels never come from workflow IDs, task IDs, exception text, adapter outputs, request data, or caller-provided strings.

## Families

- `workflow_retries`: `scheduled`, `exhausted`
- `expert_abstentions`: `deadline_exceeded`, `adapter_error`, `scope_not_authorized`, `unsupported_task`, `other`
- `workflow_stage_failures`: registered stage names only
- `workflow_recovery_outcomes`: `completed`, `already_committed`, `retry_pending`, `exhausted`, `rejected`, `failed`

All labels are enumerated at module initialization. Unknown labels raise. Counters are thread-safe, non-negative, saturating 63-bit integers; exactly 18 scalar counters are allocated.

## Privacy and limits

Counters contain no timestamps, identifiers, finding IDs, request values, exception messages, or model output. The registry resets on process restart; it is not an audit log or durable SLO database. Durable workflow audit events and evidence remain separate. No network exporter or remote collector is enabled. The metrics endpoint is local diagnostics; the service remains loopback-only.
