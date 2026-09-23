from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span

from sro.whose import KNOWN, whose


def configure_tracing(*, service_name: str, endpoint: str | None, environment: str) -> None:
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
    FastAPIInstrumentor.instrument_app(app, excluded_urls="health")


def watch_queries(engine: Any) -> None:
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


@contextmanager
def doing(what: str, **about: str | int | None) -> Iterator[Span]:
    unknown = sorted(set(about) - set(KNOWN))
    if unknown:
        raise ValueError(f"not something a span can be attributed to: {', '.join(unknown)}")
    with trace.get_tracer("sro").start_as_current_span(what) as span:
        for key, value in {**whose(), **about}.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
