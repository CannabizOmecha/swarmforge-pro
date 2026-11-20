# Privacy-Safe Local Observability

## Scope

AEGIS uses the OpenTelemetry API and SDK to create HTTP server spans. The current exporter is deliberately in-memory, bounded to 256 snapshots, and performs no network I/O. It is a local diagnostic aid, not a durable trace backend.

## Data contract

The exporter retains only:
- HTTP method from a fixed method set.
- FastAPI route template from a fixed route-template allowlist.
- Integer HTTP response status code.
- Static AEGIS service version.
- Span duration in milliseconds.

The exporter does not retain request URLs, query strings, headers, cookies, authorization values, request or response bodies, client addresses, exception messages, stack traces, span events, or links. Unknown attributes and unregistered route templates are discarded. Span snapshots are returned newest-first through the bounded GET /telemetry/spans?limit=20 endpoint.

The exporter stores only sanitized snapshots, not the SDK's raw span objects. The ring buffer overwrites the oldest snapshot at capacity and is cleared when the process restarts.

## Verification

Run:

    pytest -q tests/test_observability.py tests/test_api.py

Regression coverage verifies the attribute allowlist, rejection of unregistered routes and invalid values, bounded retention, and exclusion of sensitive query/header content.

## Limitations

This does not provide distributed context propagation, durable retention, sampling policy, a remote collector, alerting, or production SLOs. A remote exporter must not be added until authentication, transport security, data classification, retention, and user authorization are separately reviewed. Keep the API bound to 127.0.0.1.
