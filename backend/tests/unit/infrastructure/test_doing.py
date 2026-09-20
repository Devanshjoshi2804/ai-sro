"""One span, stamped with whose work it is.

The provider and the exporter have been installed since they were written, the
collector has been running, and the only spans anybody ever sent were the HTTP
request and the SQL underneath it. So a trace could say a request took ninety
seconds and not one thing about which of its model calls and browser commands
that was.
"""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from sro.infrastructure.telemetry.otel import doing
from sro.infrastructure.telemetry.whose import about

# Once for the module, because `set_tracer_provider` refuses to replace a
# provider that is already installed -- a second call warns and is ignored, so
# a per-test provider would silently send every span to the first one.
_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider()
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
trace.set_tracer_provider(_PROVIDER)


@pytest.fixture
def sent() -> InMemorySpanExporter:
    _EXPORTER.clear()
    return _EXPORTER


def test_a_span_carries_whose_work_it_is(sent: InMemorySpanExporter) -> None:
    with about(tenant="greyorange", run="run_4a57baf0", command="cmd_9f21"), doing("model.ask"):
        pass

    [span] = sent.get_finished_spans()
    assert span.name == "model.ask"
    assert span.attributes is not None
    assert span.attributes["tenant"] == "greyorange"
    assert span.attributes["run"] == "run_4a57baf0"
    assert span.attributes["command"] == "cmd_9f21"


def test_what_the_caller_adds_rides_on_top(sent: InMemorySpanExporter) -> None:
    with about(tenant="greyorange"), doing("browser.command", command="cmd_1") as span:
        span.set_attribute("kind", "ui.perform")

    [finished] = sent.get_finished_spans()
    assert finished.attributes is not None
    assert finished.attributes["command"] == "cmd_1"
    assert finished.attributes["kind"] == "ui.perform"


def test_a_span_may_not_be_attributed_to_just_anything() -> None:
    """The same closed list the log lines hold, because a span goes to the same
    collector: a customer's name must not be able to arrive as an attribute."""
    with pytest.raises(ValueError, match="customer_name"), doing("x", customer_name="ACME"):
        pass


def test_a_span_records_what_went_wrong_and_lets_it_out(sent: InMemorySpanExporter) -> None:
    """A measurement that swallows what it was measuring is worse than no
    measurement."""
    with pytest.raises(RuntimeError, match="the warehouse refused"):  # noqa: SIM117
        with doing("model.ask"):
            raise RuntimeError("the warehouse refused")

    [span] = sent.get_finished_spans()
    assert span.status.is_ok is False
    assert any("the warehouse refused" in str(event.attributes) for event in span.events)


def test_a_deployment_that_exports_nothing_still_runs() -> None:
    """`configure_tracing` installs nothing without an endpoint, so the global
    provider is the API's no-op one. This has to be safe on a hot path without
    anybody asking whether tracing is on."""
    with doing("model.ask", run="run_1") as span:
        span.set_attribute("model", "flash")
