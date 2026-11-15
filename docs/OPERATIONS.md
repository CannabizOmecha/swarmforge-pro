# Operations

## Run locally
`uvicorn aegis.api:app --host 127.0.0.1 --port 8000`

## Verify
`pytest -q`

## Safe demonstration
POST `/runs` with `{"scope_id":"local-synthetic","batch_size":20,"seed":7}`.

The final test in a batch of at least five intentionally fails a synthetic security-property fixture. It does not access a real service or disclose data.

## Stop conditions
Unknown scope, unsupported operation, over-budget batch, or any future network-enabled scope is denied. Treat missing telemetry as degraded observability, never as a clean result.

## Backups
Back up the SQLite database while the application is stopped or use SQLite's online backup mechanism. Verify restoration before relying on backups.
