"""FastAPI application. Assembled here; nothing decides policy at import time."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sro.application.execution.run_workflow import fail_orphans
from sro.config import Settings, get_settings
from sro.container import Container, build_container
from sro.domain.shared.prices import PRICES
from sro.interface.http.errors import install_error_handlers
from sro.interface.http.schemas import PROBLEMS
from sro.interface.http.v1.routers import (
    agent_channel,
    agents,
    analytics,
    ask,
    audit,
    candidates,
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
        # Said once, loudly, at the one moment somebody is watching a boot.
        #
        # A model name absent from `prices.py` records `cost_usd = 0.0` on
        # every call it makes, so the day's spend reads lower than it was and
        # the cap -- which is summed from those rows -- never trips. That is
        # the failure `prices.py` opens by describing, and it was live again:
        # three settings ran on `gemini-3.7-flash`, which the table has never
        # held, and the tenant that spent $62.89 in a day had 60 of its passes
        # recorded as free.
        #
        # A warning and not a refusal to start. A deployment mid-incident that
        # points a setting at whatever model is answering today needs to run,
        # and a boot that refuses over a price is a boot that refuses over
        # bookkeeping.
        logging.getLogger(__name__).warning(
            "these configured models are not in the price table, so their calls "
            "will record $0.00 and will not count towards the day's cap: %s",
            ", ".join(f"{name}={model}" for name, model in blind),
        )
    # Every claim in the docstring above rests on there being one process, and
    # until this line nothing checked. A second one starting -- a rolling
    # deploy, `--scale backend=2`, a restarted pod -- swept the first's live
    # runs to `failed`, which also cleared the partial unique index on running
    # runs and freed the browser for a second run to claim while the first was
    # still driving it. `Dockerfile` pins `--workers 1`; nothing enforced it.
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
    configure_logging(level="DEBUG" if get_settings().debug else "INFO")
    container = build_container()
    app.state.container = container

    await on_start(container)

    mcp_server = container.mcp_server()
    app.mount("/mcp", mcp_server.streamable_http_app(streamable_http_path="/"))
    # streamable_http_app() wires its own lifespan into the sub-app Starlette
    # returns, but FastAPI's custom `lifespan=` here replaces the default
    # walk that would trigger it -- so its session manager's task group is
    # started explicitly, in this one instead.
    async with mcp_server.session_manager.run():
        try:
            yield
        finally:
            await container.capture.stop_all()
            # The pool this process opened, closed. Left open, every app start
            # kept its connections: a reloading dev server and a suite that
            # drives the ASGI app per request both walk the database out of
            # them, and the failure lands somewhere else entirely as
            # `TooManyConnectionsError`.
            # The runs lock first, and explicitly: `dispose()` does not close
            # a connection that is still checked out, so a process that shut
            # down cleanly and started again -- a dev reload -- would find its
            # own lock still held and skip the sweep it exists to do.
            if container.driving_runs is not None:
                await container.driving_runs.close()
                container.driving_runs = None
            if container.engine is not None:
                await container.engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-SRO",
        version="0.1.0",
        summary="Workflow Builder: demonstrations in, reviewable skills out.",
        lifespan=lifespan,
    )

    # The console in local development, plus whatever a deployment names --
    # the extension's ``chrome-extension://<id>`` is the reason this is
    # configurable at all, and it cannot be defaulted because the id is per
    # build.
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

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(agents.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(confirmations.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(inbound.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(agent_channel.router, prefix="/v1")
    app.include_router(analytics.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(audit.router, prefix="/v1", responses=PROBLEMS)
    app.include_router(candidates.router, prefix="/v1", responses=PROBLEMS)
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
