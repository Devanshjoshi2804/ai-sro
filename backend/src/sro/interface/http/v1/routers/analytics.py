"""What the system has watched, noticed and done."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query

from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import SummaryModel

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def read_summary(
    container: ContainerDep,
    ctx: ContextDep,
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> SummaryModel:
    """A week by default, because a week is the unit a shift pattern repeats in."""
    summary = await container.read_summary().execute(
        ctx, since=datetime.now(UTC) - timedelta(days=days)
    )
    return SummaryModel.of(summary)
