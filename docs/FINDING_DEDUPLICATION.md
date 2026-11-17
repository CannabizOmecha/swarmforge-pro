# Cross-run Finding Deduplication

## Purpose

Repeated observations of the same security-property failure should be grouped for triage without discarding the underlying evidence.

## Fingerprint contract

Version `aegis.finding.v1` hashes canonical JSON containing:
- security property identifier;
- finding state;
- normalized security impact;
- trimmed, case-sensitive expected behavior;
- trimmed, case-sensitive observed behavior.

Only the controlled impact label is case-folded. Observed text retains case and internal whitespace because those differences can be semantically significant in security outputs.

Run IDs, finding IDs, evidence IDs, timestamps, anomaly scores, and free-form rationale are deliberately excluded because they describe an occurrence or presentation, not the core finding identity.

A fingerprint change is expected when the security property, state, impact, expected behavior, or observed behavior changes. Fingerprint versioning allows future normalization changes without silently redefining existing groups.

## Persistence semantics

Each original finding and evidence record is still persisted. In the same transaction, `finding_groups` is inserted or updated with:
- stable fingerprint and group identifier;
- first and last seen timestamps;
- occurrence count;
- first and last run identifiers;
- most recent finding identifier.

This is aggregation, not destructive deduplication. It does not merge evidence manifests or erase individual observations. A transaction failure rolls back the finding-group update together with the run bundle.

## API

- `GET /finding-groups?limit=100` returns the newest groups, with a limit from 1 through 500.
- `GET /findings` continues to return individual findings.
- `GET /metrics` includes the number of semantic finding groups.

## Limitations

The current synthetic generator demonstrates stable repeated findings. Production triage will need a benchmark of benign variation, near-duplicate defects, changed property versions, and adversarially manipulated descriptions before semantic grouping is used to suppress notifications or drive automated remediation. Existing findings created before this feature are not automatically backfilled into groups; only findings committed after the migration are indexed. A future backfill must be an explicit, idempotent migration with a dry-run and reconciliation report.

This implementation does not suppress alerts, delete findings, merge evidence, or autonomously close issues.
