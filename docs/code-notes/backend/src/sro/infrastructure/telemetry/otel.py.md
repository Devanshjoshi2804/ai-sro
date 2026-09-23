# Notes for `backend/src/sro/infrastructure/telemetry/otel.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/telemetry/otel.py`](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py#L1): Docstring

> OpenTelemetry wiring.
>
> Traces only, exported over OTLP/HTTP. Spans carry ids and counts; they never
> carry captured payloads or headers -- the telemetry plane is the one place that
> must stay safe to ship off-site. See docs/10-security-and-data.md.
>
> `doing()` is how anything in this system opens one. Until it existed the
> provider and the exporter were installed, the collector was running, and the
> only spans anybody had ever sent were the HTTP request and the SQL underneath
> it -- so a trace could say a request took ninety seconds and not one thing
> about which of its eleven steps, model calls and browser commands that was.

## `configure_tracing`, [line 19](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py#L19): Docstring

> Idempotent enough for tests: without an endpoint, nothing is installed.

## `watch_requests`, [line 34](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py#L34): Docstring

> Make the API produce the spans the exporter was always ready to send.
>
> A provider and an exporter do not make a trace: something has to open a
> span, and nothing here did. `configure_tracing` has been installing a
> perfectly good pipeline since it was written, the collector has been
> receiving nothing, and the first deployment with a trace UI showed an
> empty service list -- which reads like a broken collector and was an app
> that had never emitted a span.
>
> Excludes the health endpoint. It is polled every fifteen seconds by the
> container runtime, and a trace view where 99% of the spans are a
> healthcheck is one nobody opens twice.

## `watch_queries`, [line 38](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py#L38): Docstring

> And the database calls underneath them.
>
> Takes the async engine's `sync_engine`, which is what the instrumentation
> hooks: the events it listens for are the synchronous dialect's, and an
> `AsyncEngine` passed here instruments nothing and says nothing.

## `doing`, [line 43](../../../../../../../backend/src/sro/infrastructure/telemetry/otel.py#L43): Docstring

> One span, stamped with whose work it is.
>
> The same ids the log lines carry -- `whose()` -- so a trace and a line are
> the same story told twice and can be read against each other. Anything
> passed here is added on top and is subject to the same closed list, because
> a span goes to the same collector a log line does.
>
> A span that ends in an exception records it and lets it out: this is a
> measurement, and a measurement that swallows what it was measuring is
> worse than no measurement.
>
> Costs nothing when tracing is off. Without `configure_tracing` the global
> provider is the API's no-op one, whose spans are a shared singleton that
> records nothing -- so this is safe to put on a hot path without asking
> whether a deployment exports anything.
