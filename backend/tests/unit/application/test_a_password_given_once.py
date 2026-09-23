"""A password an operator gives for one run, and nothing after it.

The vault keeps a credential somebody means to keep. This is the other answer
to the same question -- "use it now, do not keep it" -- and what these check
is that it behaves like that answer and not like a second, quieter vault: one
read by the run it was given for, a quarter of an hour, and never written
down.
"""

from __future__ import annotations

import pytest

from sro.application.execution.one_time_secrets import K_HELD_FOR, OneTimeSecrets


@pytest.fixture
def secrets() -> OneTimeSecrets:
    return OneTimeSecrets()


def test_it_is_handed_out_exactly_once(secrets: OneTimeSecrets) -> None:
    """The whole of "just this once". A value that answered twice would be a
    vault entry with a shorter name for itself."""
    secrets.hold("acme/wms.test/password", "hunter2", run_id="run_a", now=1000.0)

    assert secrets.take("acme/wms.test/password", run_id="run_a", now=1001.0) == "hunter2"
    assert secrets.take("acme/wms.test/password", run_id="run_a", now=1002.0) is None


def test_a_secret_held_for_one_run_is_not_given_to_another(secrets: OneTimeSecrets) -> None:
    """The property this door exists for: a password given for a run only ever
    reaches that run, and a different run asking gets nothing -- not even the
    chance to take it later."""
    secrets.hold("acme/wms.test/password", "hunter2", run_id="run_a", now=1000.0)

    assert secrets.take("acme/wms.test/password", run_id="run_b", now=1001.0) is None
    # And the run it was actually given for can still take it.
    assert secrets.take("acme/wms.test/password", run_id="run_a", now=1002.0) == "hunter2"


def test_it_is_forgotten_after_its_quarter_of_an_hour(secrets: OneTimeSecrets) -> None:
    """A password nobody used is not still in memory at the end of a shift."""
    secrets.hold("acme/wms.test/password", "hunter2", run_id="run_a", now=1000.0)

    assert secrets.waiting("acme/wms.test/password", now=1000.0 + K_HELD_FOR - 1) is True
    assert (
        secrets.take("acme/wms.test/password", run_id="run_a", now=1000.0 + K_HELD_FOR + 1) is None
    )


def test_an_expired_entry_is_gone_after_the_sweep_even_if_never_taken(
    secrets: OneTimeSecrets,
) -> None:
    """The sweep runs on every hold and every take, not only when the key
    somebody asks about happens to be the one that aged out."""
    secrets.hold("acme/wms.test/password", "hunter2", run_id="run_a", now=1000.0)

    # A second, unrelated key holds -- which sweeps the first away, long after
    # its own quarter of an hour, without anybody ever taking it.
    secrets.hold("acme/other.test/password", "irrelevant", run_id="run_z", now=2000.0)

    assert secrets.waiting("acme/wms.test/password", now=2000.0) is False
    assert secrets.take("acme/wms.test/password", run_id="run_a", now=2000.0) is None


def test_typing_it_again_replaces_the_first(secrets: OneTimeSecrets) -> None:
    """Somebody who types it twice meant the second one -- they mistyped the
    first, which is the whole reason they are typing it again."""
    secrets.hold("acme/wms.test/password", "wrong", run_id="run_a", now=1000.0)
    secrets.hold("acme/wms.test/password", "right", run_id="run_a", now=1010.0)

    assert secrets.take("acme/wms.test/password", run_id="run_a", now=1011.0) == "right"


def test_one_system_is_not_another(secrets: OneTimeSecrets) -> None:
    secrets.hold("acme/wms.test/password", "hunter2", run_id="run_a", now=1000.0)

    assert secrets.take("acme/other.test/password", run_id="run_a", now=1001.0) is None
    assert secrets.take("acme/wms.test/password", run_id="run_a", now=1001.0) == "hunter2"


async def test_the_runner_takes_it_before_the_vault_and_only_once() -> None:
    """The lookup a step goes through. A value given for one run beats the
    stored one -- an operator typing a password into the card is answering
    about the run in front of them, not rotating what the deployment keeps --
    and the run after that is back on the vault."""
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from tests.unit.fakes import FakeCredentialVault, FakeUnitOfWork

    vault = FakeCredentialVault()
    await vault.store("acme/wms.test/password", "the-stored-one")
    secrets = OneTimeSecrets()
    runs = StartWorkflowRun(
        FakeUnitOfWork(),
        channel=None,
        asker=None,
        plan_model="m",
        rescue_model="m",
        clock=lambda: 0.0,
        cap_usd=1.0,
        stops=None,
        approvals=None,
        one_time_secrets=secrets,
        vault=vault,
    )

    secrets.hold("acme/wms.test/password", "typed-just-now", run_id="run_a")

    assert await runs._secret_for("run_a", "acme/wms.test/password") == "typed-just-now"
    assert await runs._secret_for("run_a", "acme/wms.test/password") == "the-stored-one"


async def test_a_password_held_for_one_run_is_not_read_by_another() -> None:
    """The same property, through the door a step actually calls: a run that
    did not receive the password falls straight through to the vault, rather
    than reading what an operator lent to a different run."""
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from tests.unit.fakes import FakeUnitOfWork

    secrets = OneTimeSecrets()
    runs = StartWorkflowRun(
        FakeUnitOfWork(),
        channel=None,
        asker=None,
        plan_model="m",
        rescue_model="m",
        clock=lambda: 0.0,
        cap_usd=1.0,
        stops=None,
        approvals=None,
        one_time_secrets=secrets,
    )

    secrets.hold("acme/wms.test/password", "typed-just-now", run_id="run_a")

    assert await runs._secret_for("run_b", "acme/wms.test/password") is None
    assert await runs._secret_for("run_a", "acme/wms.test/password") == "typed-just-now"


async def test_with_no_vault_at_all_a_password_given_once_still_signs_in() -> None:
    """A deployment that keeps no credentials is one somebody can still sign
    into by hand, which is half the point of this door."""
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from tests.unit.fakes import FakeUnitOfWork

    secrets = OneTimeSecrets()
    runs = StartWorkflowRun(
        FakeUnitOfWork(),
        channel=None,
        asker=None,
        plan_model="m",
        rescue_model="m",
        clock=lambda: 0.0,
        cap_usd=1.0,
        stops=None,
        approvals=None,
        one_time_secrets=secrets,
    )

    secrets.hold("acme/wms.test/password", "typed-just-now", run_id="run_a")

    assert await runs._secret_for("run_a", "acme/wms.test/password") == "typed-just-now"
    assert await runs._secret_for("run_a", "acme/wms.test/password") is None
