"""OpenTelemetry wiring.

Traces only, exported over OTLP/HTTP. Spans carry ids and counts; they never
carry captured payloads or headers -- the telemetry plane is the one place that
must stay safe to ship off-site. See docs/10-security-and-data.md.
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
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


def watch_requests(app: Any) -> None:
    """Make the API produce the spans the exporter was always ready to send.

    A provider and an exporter do not make a trace: something has to open a
    span, and nothing here did. `configure_tracing` has been installing a
    perfectly good pipeline since it was written, the collector has been
    receiving nothing, and the first deployment with a trace UI showed an
    empty service list -- which reads like a broken collector and was an app
    that had never emitted a span.

    Excludes the health endpoint. It is polled every fifteen seconds by the
    container runtime, and a trace view where 99% of the spans are a
    healthcheck is one nobody opens twice.
    """
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")


def watch_queries(engine: Any) -> None:
    """And the database calls underneath them.

    Takes the async engine's `sync_engine`, which is what the instrumentation
    hooks: the events it listens for are the synchronous dialect's, and an
    `AsyncEngine` passed here instruments nothing and says nothing.
    """
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
