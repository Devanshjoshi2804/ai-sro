"""A password given "just this once" on a Steel run's card reaches the worker that signs in.

The api takes the answer; the worker signs the run in. A value held in the api's
memory never reached the worker: the run read the vault's old, refused password
and stopped again ("had its password refused"), however many times it was typed
(QA, 2026-10-01). It is held where both read it -- the vault, under the run's own
key -- and taken by the run's sign-in exactly once.
"""

from __future__ import annotations

from sro.application.execution.one_time_secrets import K_HELD_FOR, HeldForTheRun
from tests.unit.fakes import FakeCredentialVault

KEY = "greyorange/keycloak.example/rkuchiyagm/password"


async def test_what_one_process_holds_another_takes_exactly_once() -> None:
    vault = FakeCredentialVault()
    await HeldForTheRun(vault, clock=lambda: 1000.0).hold(KEY, "s3cret", run_id="run_a")

    worker = HeldForTheRun(vault, clock=lambda: 1001.0)

    assert await worker.take(KEY, run_id="run_a") == "s3cret"
    assert await worker.take(KEY, run_id="run_a") is None


async def test_it_is_never_the_vault_password_and_never_another_runs() -> None:
    vault = FakeCredentialVault()
    held = HeldForTheRun(vault, clock=lambda: 1000.0)
    await held.hold(KEY, "s3cret", run_id="run_a")

    assert await vault.get(KEY) is None
    assert await held.take(KEY, run_id="run_b") is None
    assert await held.take(KEY, run_id="run_a") == "s3cret"


async def test_after_its_quarter_of_an_hour_it_is_gone() -> None:
    vault = FakeCredentialVault()
    await HeldForTheRun(vault, clock=lambda: 1000.0).hold(KEY, "s3cret", run_id="run_a")

    late = HeldForTheRun(vault, clock=lambda: 1000.0 + K_HELD_FOR + 1)

    assert await late.take(KEY, run_id="run_a") is None
    assert await late.take(KEY, run_id="run_a") is None
