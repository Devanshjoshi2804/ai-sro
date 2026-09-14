"""The vault a deployment uses, written before the deploy rather than during it.

`file_vault` is the laptop; this is Secret Manager behind the same three
methods. What is worth testing without a Google project is exactly what would
have been found at three in the morning: what a key becomes, what absence
means, and what a store that cannot be reached does.

The client is faked at its own four calls. A fake that had to implement
`SecretManagerServiceClient` is a fake nobody writes, and those four are the
whole of what a vault is.
"""

from __future__ import annotations

import pytest
from google.api_core import exceptions

from sro.application.ports.vault import VaultUnavailable
from sro.infrastructure.vault.secret_manager import MAX_ID, SecretManagerVault, secret_id_for


def _as_google_refuses(kind: type[Exception], said: str) -> Exception:
    """One of Google's exceptions, raised the way the client raises it.

    One function rather than five call sites, because the client's own
    exceptions are what a fake has to raise for the adapter's `except` clauses
    to mean anything -- and because the suite's disabled-code list is a ratchet
    that only turns one way, so `no-untyped-call` does not go on it for this.
    """
    return kind(said)


PROJECT = "sro-prod"
KEY = "new/keycloak.example/password"
KEPT = "not-in-any-fixture-2f71"


class _Fake:
    """One project's secrets, in memory, refusing the way Google refuses."""

    def __init__(self, *, refuse: Exception | None = None) -> None:
        self.versions: dict[str, list[bytes]] = {}
        self.created: list[str] = []
        self.refuse = refuse

    def create_secret(self, request: dict[str, object]) -> object:
        if self.refuse:
            raise self.refuse
        name = f"{request['parent']}/secrets/{request['secret_id']}"
        if name in self.versions:
            raise _as_google_refuses(exceptions.AlreadyExists, name)
        self.created.append(name)
        self.versions[name] = []
        return object()

    def add_secret_version(self, request: dict[str, object]) -> object:
        if self.refuse:
            raise self.refuse
        payload = request["payload"]
        assert isinstance(payload, dict)
        self.versions.setdefault(str(request["parent"]), []).append(bytes(payload["data"]))
        return object()

    def access_secret_version(self, request: dict[str, object]) -> object:
        if self.refuse:
            raise self.refuse
        name = str(request["name"]).removesuffix("/versions/latest")
        kept = self.versions.get(name)
        if not kept:
            raise _as_google_refuses(exceptions.NotFound, name)
        return type("Answered", (), {"payload": type("Payload", (), {"data": kept[-1]})})

    def delete_secret(self, request: dict[str, object]) -> object:
        if self.refuse:
            raise self.refuse
        name = str(request["name"])
        if name not in self.versions:
            raise _as_google_refuses(exceptions.NotFound, name)
        del self.versions[name]
        return object()


def _vault(fake: _Fake) -> SecretManagerVault:
    return SecretManagerVault(project=PROJECT, client=fake)


# --- what a key becomes -----------------------------------------------------


def test_a_key_becomes_an_id_that_is_still_readable() -> None:
    assert secret_id_for(KEY).startswith("new_keycloak-example_password__")


def test_two_keys_that_flatten_the_same_way_are_still_two_secrets() -> None:
    """The reason the digest is there at all. Substitution alone puts `a/b` and
    `a-b` in one secret, which is one tenant reading another tenant's
    password."""
    assert secret_id_for("t/a/b") != secret_id_for("t/a-b")


def test_the_same_key_is_the_same_id_in_every_process() -> None:
    # A vault whose ids depended on a hash seed would lose every secret it
    # wrote the moment the process restarted.
    assert secret_id_for(KEY) == secret_id_for(KEY)


def test_a_long_key_fits_and_keeps_the_end_that_says_whose_it_is() -> None:
    """Truncated from the front of the readable part: the head of these keys is
    the tenant, and an id that kept `password` while losing which tenant it
    belongs to is worse than an unreadable one."""
    made = secret_id_for("new/" + "x" * 400 + "/password")

    assert len(made) <= MAX_ID
    assert made.endswith(secret_id_for("new/" + "x" * 400 + "/password")[-13:])


# --- what it does --------------------------------------------------------


async def test_what_is_stored_comes_back() -> None:
    fake = _Fake()
    vault = _vault(fake)

    await vault.store(KEY, KEPT)

    assert await vault.get(KEY) == KEPT


async def test_storing_twice_is_a_rotation_and_not_a_second_secret() -> None:
    """Secret Manager separates the container from its versions, and rotation
    is what `store` is for -- so the second write adds a version and the
    `AlreadyExists` it gets for the container is the ordinary path."""
    fake = _Fake()
    vault = _vault(fake)

    await vault.store(KEY, KEPT)
    await vault.store(KEY, "the-new-one-8c13")

    assert await vault.get(KEY) == "the-new-one-8c13"
    assert len(fake.created) == 1


async def test_a_secret_nobody_stored_is_absence_and_not_a_failure() -> None:
    """What the port promises callers decide the meaning of -- and a step that
    types a password decides it means "nobody stored one" and refuses by name
    rather than typing a blank into a login form."""
    assert await _vault(_Fake()).get(KEY) is None


async def test_deleting_one_that_is_not_there_is_success() -> None:
    # The port says idempotent, in those words.
    await _vault(_Fake()).delete(KEY)


async def test_deleting_removes_it() -> None:
    fake = _Fake()
    vault = _vault(fake)
    await vault.store(KEY, KEPT)

    await vault.delete(KEY)

    assert await vault.get(KEY) is None


# --- what a store that cannot be reached does -------------------------------


async def test_a_store_that_refuses_a_read_is_unavailable_and_never_absent() -> None:
    """The distinction this adapter exists to get right. Answering `None` for
    a denied IAM call or a dropped network would tell a run that nobody had
    stored a password, when the truth is that nobody could ask."""
    vault = _vault(_Fake(refuse=_as_google_refuses(exceptions.PermissionDenied, "no access")))

    with pytest.raises(VaultUnavailable, match="could not be read"):
        await vault.get(KEY)


async def test_a_store_that_refuses_a_write_says_so() -> None:
    vault = _vault(
        _Fake(refuse=_as_google_refuses(exceptions.ServiceUnavailable, "backend is down"))
    )

    with pytest.raises(VaultUnavailable, match="refused a write"):
        await vault.store(KEY, KEPT)


def test_a_project_nobody_named_is_refused_at_construction() -> None:
    # Not at first use: an empty project is a deployment misconfigured, and it
    # can say so while somebody is still looking at the deploy.
    with pytest.raises(VaultUnavailable, match="name the Google project"):
        SecretManagerVault(project="   ", client=_Fake())
