"""FastAPI application. Assembled here; nothing decides policy at import time."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sro.application.execution.run_workflow import fail_orphans
from sro.config import Settings, get_settings
from sro.container import Container, build_container, instrument
from sro.domain.shared.prices import PRICES
from sro.interface.http.errors import install_error_handlers
from sro.interface.http.schemas import PROBLEMS
from sro.interface.http.v1.routers import (
    agent_channel,
    agents,
    analytics,
    ask,
    audit,
    chat,
    confirmations,
    connections,
    devices,
    health,
    inbound,
    intent,
    knowledge,
    lookups,
    mine,
    observations,
    offers,
    pool,
    read_gestures,
    recordings,
    runs,
    secrets,
    shapes,
    skills,
    spend,
    stream,
    threads,
    triggers,
    watch,
    workflow_runs,
    workflows,
)
from sro.observability import configure_logging
from sro.whose import about

logger = logging.getLogger("sro.http")
"""The access log. Named for what it is rather than for this module: somebody
turning the request line up or down is not looking for `sro.interface.http.app`.
"""

_QUIET = frozenset({"/health", "/metrics"})


async def on_start(container: Container) -> int:
    """What a fresh process has to put right before it serves anything.

    Every run still `running` when this starts belongs to a process that is
    gone. `fail_orphans` has said "called once at startup" since it was written
    and nothing called it, so a run whose task died -- a reload in development,
    a deploy in production -- sat `running` forever: the console kept it on
    "Needs a person", the extension kept asking after it on every heartbeat,
    and an Approve on it recorded a person's name against a write that was
    never going to be sent. An operator hit exactly that.

    Safe here because `claim_the_runs` makes it so: a Postgres advisory lock
    held for the life of the process, and a process that cannot take it does
    not sweep. One API worker owns every run until runs become Temporal
    workflows -- the same assumption the in-process device sockets and the
    approval register already make, and the same thing that has to change with
    them. The difference is that the assumption is now checked rather than
    written down.

    Its own function rather than four lines inside `lifespan`, because
    `lifespan` builds the real container and mounts the MCP app: a test that
    wanted to know whether startup sweeps would have to stand up both.
    """
    blind = unpriced_models(container.settings)
    if blind:
        logging.getLogger(__name__).warning(
            "these configured models are not in the price table, so their calls "
            "will record $0.00 and will not count towards the day's cap: %s",
            ", ".join(f"{name}={model}" for name, model in blind),
        )
    if not await container.claim_the_runs():
        logging.getLogger(__name__).warning(
            "another API process is driving runs, so this one swept none. "
            "Runs, approvals and device sockets all live in one process: "
            "check that this deployment really means to run two"
        )
        return 0
    async with container.unit_of_work() as uow:
        swept = await fail_orphans(uow, "the process driving this run stopped")
    if swept:
        logging.getLogger(__name__).warning(
            "swept %d run(s) left running by a process that is gone", swept
        )
    return swept


def unpriced_models(settings: Settings) -> list[tuple[str, str]]:
    """Every `gemini_*_model` setting whose value `prices.py` cannot price.

    Read off the settings object rather than a list kept here: a setting added
    next month is covered by this the day it exists, and a list of names to
    check is a list that goes stale exactly when it matters.
    """
    return sorted(
        (name, model)
        for name in dir(settings)
        if name.startswith("gemini_") and name.endswith("model")
        if isinstance(model := getattr(settings, name), str) and model
        if model not in PRICES
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(
        level="DEBUG" if settings.debug else "INFO",
        as_json=settings.environment != "local",
        louder_for=frozenset(one.strip() for one in settings.louder_for.split(",") if one.strip()),
    )
    container = build_container()
    app.state.container = container

    await on_start(container)

    mcp_server = container.mcp_server()
    app.mount("/mcp", mcp_server.streamable_http_app(streamable_http_path="/"))
    async with mcp_server.session_manager.run():
        try:
            yield
        finally:
            await container.capture.stop_all()
            if container.driving_runs is not None:
                await container.driving_runs.close()
                container.driving_runs = None
            if container.engine is not None:
                await container.engine.dispose()


class Attributing:
    """Every line a request writes says which request it was and whose -- and
    one line per request says what came of it.

    **Pure ASGI, and that is the whole reason this is a class.** Starlette runs
    an `http` middleware's downstream app in a SEPARATE task, so every id a
    route establishes -- the tenant and the principal off the credential, the
    device, the thread -- is set in a context the middleware never sees. Those
    ids ride on the task, so the line that reports the request has to be
    written in the task that served it.

    Which is the line this system did not have. uvicorn's access log is written
    from the protocol layer once the response is done, outside the task the
    handlers ran in: it carries the path and the status and nobody at all. On a
    deployment with twenty tenants, the one line written for every request was
    the one line that could not be attributed to any of them -- and a request
    that reached a route and said nothing existed only there.

    The id is the client's own where it sent one. A console and an extension
    that carry `x-request-id` through can then be joined to what the backend
    did with it, which is the join somebody debugging a button actually needs.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self._app(scope, receive, send)
            return
        given = _header(scope, b"x-request-id")[:64]
        status = 0

        async def watched(message: Any) -> None:
            nonlocal status
            if message.get("type") == "http.response.start":
                status = int(message.get("status") or 0)
            await send(message)

        began = perf_counter()
        with about(request=given or f"req_{uuid4().hex[:12]}"):
            try:
                await self._app(scope, receive, watched)
            finally:
                _arrived(scope, status, (perf_counter() - began) * 1000)


def _header(scope: Any, wanted: bytes) -> str:
    for name, value in scope.get("headers") or ():
        if name.lower() == wanted:
            return str(value.decode("latin-1")).strip()
    return ""


def _arrived(scope: Any, status: int, took_ms: float) -> None:
    """The one line per request, with whoever it turned out to be on it.

    `0` where nothing ever started a response: the request was cut off, or the
    server is going down under it. Said rather than skipped -- a request that
    produced no response at all is the one somebody is looking for.

    The health check is a line every fifteen seconds saying a process is a
    process, which at INFO is six thousand lines a day of nothing between the
    lines somebody is reading. It is still written, at DEBUG, because a
    deployment where it STOPS is a deployment somebody wants the record of.
    """
    logger.log(
        logging.DEBUG if scope.get("path") in _QUIET else logging.INFO,
        "%s %s %s in %dms",
        scope.get("method", "?"),
        scope.get("path", "?"),
        status or "no answer",
        took_ms,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-SRO",
        version="0.1.0",
        summary="Workflow Builder: demonstrations in, reviewable skills out.",
        lifespan=lifespan,
    )

    origins = list(settings.cors_origins)
    if settings.environment == "local":
        origins.append("http://localhost:3000")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(Attributing)

    if settings.otlp_endpoint:
        instrument(app)

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(agents.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(confirmations.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(inbound.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(agent_channel.router, prefix="/v1")
    app.include_router(analytics.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(audit.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(ask.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(chat.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(secrets.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(lookups.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(connections.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(devices.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(mine.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(observations.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(offers.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(pool.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(read_gestures.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(recordings.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(skills.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(shapes.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(spend.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(intent.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(stream.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(knowledge.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(threads.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(triggers.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(runs.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(watch.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(workflows.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(workflow_runs.router, prefix="/v1", responses=PROBLEMS)
    return app


app = create_app()
