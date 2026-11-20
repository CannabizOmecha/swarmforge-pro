from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from aegis.observability import SERVICE_VERSION, BoundedSpanExporter, sanitize_span_attributes


def test_span_attribute_allowlist_drops_sensitive_and_unrecognized_values():
    clean = sanitize_span_attributes(
        {
            "http.request.method": "GET",
            "http.route": "/runs/{run_id}",
            "http.response.status_code": 200,
            "service.version": SERVICE_VERSION,
            "url.full": "https://example.invalid/?token=private",
            "authorization": "Bearer private-token",
            "user.email": "person@example.com",
            "http.route.raw": "/runs/private-run-id",
        }
    )
    assert clean == {
        "http.request.method": "GET",
        "http.route": "/runs/{run_id}",
        "http.response.status_code": 200,
        "service.version": SERVICE_VERSION,
    }
    assert "private" not in repr(clean)
    assert "person@example.com" not in repr(clean)


def test_span_attribute_allowlist_rejects_unregistered_route_and_invalid_values():
    clean = sanitize_span_attributes(
        {
            "http.request.method": "GET /private/path",
            "http.route": "/runs/private-run-id",
            "http.response.status_code": 999,
            "service.version": "attacker-controlled",
        }
    )
    assert clean == {}


def test_exporter_is_bounded_and_retains_only_sanitized_snapshots():
    exporter = BoundedSpanExporter(max_spans=2)
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("aegis.test")
    for _ in range(3):
        with tracer.start_as_current_span("http.server.request") as span:
            span.set_attribute("http.request.method", "GET")
            span.set_attribute("http.route", "/health")
            span.set_attribute("http.response.status_code", 200)
            span.set_attribute("authorization", "Bearer must-not-be-retained")
    snapshots = exporter.get_spans(limit=2)
    assert len(snapshots) == 2
    assert exporter.retained_count == 2
    assert all(snapshot["name"] == "http.server.request" for snapshot in snapshots)
    assert all(
        set(snapshot["attributes"])
        <= {
            "http.request.method",
            "http.route",
            "http.response.status_code",
            "service.version",
        }
        for snapshot in snapshots
    )
    assert "must-not-be-retained" not in repr(snapshots)
    provider.shutdown()


def test_exporter_rejects_unbounded_query_limits():
    exporter = BoundedSpanExporter(max_spans=2)
    for limit in (0, 101):
        try:
            exporter.get_spans(limit)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid span query limit was accepted")
