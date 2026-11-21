from contextlib import contextmanager
from collections import deque
from collections.abc import Mapping, Sequence
from threading import Lock

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

SERVICE_VERSION = "0.6.6"
MAX_RETAINED_SPANS = 256
MAX_QUERY_SPANS = 100

WORKFLOW_STAGES = frozenset({"authorize", "execute", "checkpoint", "commit", "resume"})
WORKFLOW_OUTCOMES = frozenset({"success", "failure", "rejected", "retry"})

HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
ROUTE_TEMPLATES = frozenset(
    {
        "/health", "/agents", "/agent-tasks", "/agent-pipelines/validate",
        "/routing/{task}", "/scope", "/runs", "/workflows/{workflow_id}",
        "/workflows/{workflow_id}/resume", "/runs/{run_id}", "/runs/{run_id}/replay",
        "/evidence/{evidence_id}", "/evidence/{evidence_id}/verify",
        "/finding-groups", "/findings", "/audit/verify", "/audit/events",
        "/metrics", "/telemetry/spans", "unmatched",
    }
)


def normalize_http_method(value: str) -> str:
    method = value.upper()
    return method if method in HTTP_METHODS else "OTHER"


def route_template_for_scope(scope: Mapping[str, object]) -> str:
    route = scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str) and template in ROUTE_TEMPLATES:
        return template
    return "unmatched"


def sanitize_span_attributes(attributes: Mapping[str, object]) -> dict[str, str | int]:
    """Retain only fixed, low-cardinality request metadata; never retain free-form values."""
    clean: dict[str, str | int] = {}
    method = attributes.get("http.request.method")
    if isinstance(method, str) and method in HTTP_METHODS:
        clean["http.request.method"] = method
    route = attributes.get("http.route")
    if isinstance(route, str) and route in ROUTE_TEMPLATES:
        clean["http.route"] = route
    status_code = attributes.get("http.response.status_code")
    if type(status_code) is int and 100 <= status_code <= 599:
        clean["http.response.status_code"] = status_code
    service_version = attributes.get("service.version")
    if service_version == SERVICE_VERSION:
        clean["service.version"] = SERVICE_VERSION
    stage = attributes.get("aegis.workflow.stage")
    if isinstance(stage, str) and stage in WORKFLOW_STAGES:
        clean["aegis.workflow.stage"] = stage
    outcome = attributes.get("aegis.workflow.outcome")
    if isinstance(outcome, str) and outcome in WORKFLOW_OUTCOMES:
        clean["aegis.workflow.outcome"] = outcome
    return clean


@contextmanager
def workflow_stage(stage: str):
    """Trace a fixed workflow stage using only allowlisted, low-cardinality metadata."""
    if stage not in WORKFLOW_STAGES:
        raise ValueError("workflow stage is not registered")
    with TRACER.start_as_current_span(
        "internal.operation", attributes={"aegis.workflow.stage": stage}
    ) as span:
        try:
            yield span
        except Exception:
            span.set_attribute("aegis.workflow.outcome", "failure")
            raise
        else:
            span.set_attribute("aegis.workflow.outcome", "success")


class BoundedSpanExporter(SpanExporter):
    """In-memory exporter that stores sanitized snapshots and never performs network I/O."""

    def __init__(self, max_spans: int = MAX_RETAINED_SPANS) -> None:
        if max_spans < 1:
            raise ValueError("max_spans must be positive")
        self.max_spans = max_spans
        self._spans: deque[dict[str, object]] = deque(maxlen=max_spans)
        self._lock = Lock()
        self._shutdown = False

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            if self._shutdown:
                return SpanExportResult.FAILURE
            for span in spans:
                start_time = span.start_time or 0
                end_time = span.end_time or start_time
                duration_ms = round(max(0, end_time - start_time) / 1_000_000, 3)
                self._spans.append(
                    {
                        "name": "http.server.request"
                        if span.name == "http.server.request"
                        else "internal.operation",
                        "duration_ms": duration_ms,
                        "attributes": sanitize_span_attributes(span.attributes or {}),
                    }
                )
        return SpanExportResult.SUCCESS

    def get_spans(self, limit: int = 20) -> list[dict[str, object]]:
        if not 1 <= limit <= MAX_QUERY_SPANS:
            raise ValueError(f"limit must be between 1 and {MAX_QUERY_SPANS}")
        with self._lock:
            selected = list(self._spans)[-limit:]
        return [
            {
                "name": span["name"],
                "duration_ms": span["duration_ms"],
                "attributes": dict(span["attributes"]),
            }
            for span in reversed(selected)
        ]

    @property
    def retained_count(self) -> int:
        with self._lock:
            return len(self._spans)

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        return True

    def shutdown(self) -> None:
        with self._lock:
            self._shutdown = True


SPAN_EXPORTER = BoundedSpanExporter()
TRACER_PROVIDER = TracerProvider(
    resource=Resource.create({"service.name": "aegis-moe", "service.version": SERVICE_VERSION})
)
TRACER_PROVIDER.add_span_processor(SimpleSpanProcessor(SPAN_EXPORTER))
TRACER = TRACER_PROVIDER.get_tracer("aegis.observability", SERVICE_VERSION)
