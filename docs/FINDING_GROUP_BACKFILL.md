# Historical Finding-Group Backfill

## Why this exists

Cross-run finding groups were introduced after some findings may already have
been persisted. The original \`findings\` rows remain the source of truth, while
\`finding_groups\` is a derived index. This command reconciles the index without
deleting or rewriting original findings or evidence.

## Safe procedure

From the repository root, first preview the existing local database:

\`\`\`bash
python -m aegis.backfill --database data/aegis.sqlite3
\`\`\`

The default mode does not change finding or finding-group rows. Review the
source-finding count, expected group count, and whether the derived index differs.

Only after reviewing the preview, apply the rebuild:

\`\`\`bash
python -m aegis.backfill --database data/aegis.sqlite3 --apply
\`\`\`

Use the actual database path for the local installation. The command refuses
to initialize a missing database.

## Guarantees and limits

- Every source row is parsed using the strict Pydantic \`Finding\` model.
- The database row ID must match the finding ID in its payload.
- Apply mode takes a SQLite \`BEGIN IMMEDIATE\` write lock before reading source
  findings, then validates all rows before changing the derived index.
- Rebuild and its hash-chained audit event commit in one transaction.
- Invalid source data aborts the transaction; existing groups remain intact.
- Group ordering is deterministic by normalized UTC timestamp and finding ID.
- Repeated application is a no-op when the index already matches the source.
- A changed rebuild appends one \`finding_groups.rebuilt\` audit event. A no-op
  does not add another event.
- Original findings and evidence are never deleted, merged, or rewritten.

This is a single-node SQLite maintenance operation. It is not an online
multi-writer migration service, and it does not repair malformed source findings.
Back up the database before applying maintenance to a valuable local dataset.
