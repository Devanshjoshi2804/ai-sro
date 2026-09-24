from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from urllib.parse import quote

from sro.domain.shared.hosts import system_of

K_LEASE_TTL = timedelta(minutes=2)

K_VAULT_VALUE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class Account:
    tenant: str
    origin: str
    username: str

    @classmethod
    def of(cls, tenant: str, system: str, username: str) -> Account:
        return cls(tenant, system_of(system) or system.strip().lower(), username.strip())

    @property
    def key(self) -> str:
        return f"{self.tenant}/{self.origin}/{quote(self.username.casefold(), safe='@+-_')}"

    def vault_key(self, what: Literal["password", "state"]) -> str:
        return f"{self.key}/{what}"

    @property
    def lock_id(self) -> int:
        return int.from_bytes(hashlib.sha256(self.key.encode()).digest()[:8], "big", signed=True)


class LeaseState(StrEnum):
    SIGNING_IN = "signing_in"
    READY = "ready"
    EXPIRED = "expired"
    BROKEN = "broken"


LIVE = frozenset({LeaseState.SIGNING_IN, LeaseState.READY})


@dataclass(frozen=True, slots=True)
class Lease:
    id: str
    account: Account
    container_url: str
    steel_session_id: str
    holder: str
    heartbeat_at: datetime
    expires_at: datetime
    state: LeaseState

    def live(self, now: datetime) -> bool:
        return self.state in LIVE and now < self.expires_at


def new_lease_id() -> str:
    return "lse_" + secrets.token_hex(16)
