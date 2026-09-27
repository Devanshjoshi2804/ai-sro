from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class JobAlias:
    wording: str
    field: str
    confirmed_by: str
    at: datetime
    role: str = ""
