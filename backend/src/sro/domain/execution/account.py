from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from urllib.parse import quote

from sro.domain.execution.secrets import as_key
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.hosts import origin_of

K_LEASE_TTL = timedelta(minutes=2)

K_VAULT_VALUE_BYTES = 64 * 1024

K_USERNAME_MAX_LEN = 254


@dataclass(frozen=True, slots=True)
class Account:
    tenant: str
    origin: str
    username: str

    @classmethod
    def of(cls, tenant: str, system: str, username: str) -> Account:
        trimmed = username.strip()
        if not trimmed or len(trimmed) > K_USERNAME_MAX_LEN:
            raise InvariantViolation("an account needs a username")
        return cls(tenant, origin_of(system), trimmed)

    @property
    def key(self) -> str:
        return f"{self.tenant}/{self.origin}/{_encoded(self.username)}"

    def vault_key(self, field: str) -> str:
        normalized = as_key(field)
        if not normalized:
            raise InvariantViolation("a field needs a name")
        return f"{self.key}/{normalized}"

    @property
    def lock_id(self) -> int:
        return int.from_bytes(hashlib.sha256(self.key.encode()).digest()[:8], "big", signed=True)


def _encoded(username: str) -> str:
    quoted = quote(username.casefold(), safe="")
    return quoted.replace(".", "%2E").replace("~", "%7E")


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
    context_id: str
    holder: str
    heartbeat_at: datetime
    expires_at: datetime
    state: LeaseState

    def live(self, now: datetime) -> bool:
        return self.state in LIVE and now < self.expires_at


def new_lease_id() -> str:
    return "lse_" + secrets.token_hex(16)
