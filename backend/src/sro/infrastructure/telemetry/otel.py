"""OpenTelemetry wiring.

Traces only, exported over OTLP/HTTP. Spans carry ids and counts; they never
carry captured payloads or headers -- the telemetry plane is the one place that
must stay safe to ship off-site. See docs/10-security-and-data.md.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_tracing(*, service_name: str, endpoint: str | None, environment: str) -> None:
    """Idempotent enough for tests: without an endpoint, nothing is installed."""
    if endpoint is None:
        return

    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": service_name, "deployment.environment": environment}
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)


def tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
