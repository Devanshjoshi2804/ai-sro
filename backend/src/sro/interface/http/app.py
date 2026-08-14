"""FastAPI application. Assembled here; nothing decides policy at import time."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sro.config import get_settings
from sro.container import build_container
from sro.interface.http.errors import install_error_handlers
from sro.interface.http.v1.routers import (
    connections,
    health,
    intent,
    recordings,
    runs,
    skills,
    threads,
)
from sro.observability import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(level="DEBUG" if get_settings().debug else "INFO")
    container = build_container()
    app.state.container = container
    try:
        yield
    finally:
        await container.capture.stop_all()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-SRO",
        version="0.1.0",
        summary="Workflow Builder: demonstrations in, reviewable skills out.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if settings.environment == "local" else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(connections.router, prefix="/v1")
    app.include_router(recordings.router, prefix="/v1")
    app.include_router(skills.router, prefix="/v1")
    app.include_router(intent.router, prefix="/v1")
    app.include_router(threads.router, prefix="/v1")
    app.include_router(runs.router, prefix="/v1")
    return app


app = create_app()
