from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import Pool


def create_engine(
    database_url: str, *, echo: bool = False, poolclass: type[Pool] | None = None
) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True, poolclass=poolclass)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
