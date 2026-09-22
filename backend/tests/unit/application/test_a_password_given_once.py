"""A password an operator gives for one run, and nothing after it.

The vault keeps a credential somebody means to keep. This is the other answer
to the same question -- "use it now, do not keep it" -- and what these check
is that it behaves like that answer and not like a second, quieter vault: one
read, a quarter of an hour, and never written down.
"""

from __future__ import annotations

import pytest

from sro.application.execution.one_time_secrets import (
    K_HELD_FOR,
    forget_everything,
    hold,
    take,
    waiting,
)


@pytest.fixture(autouse=True)
def _clean() -> None:
    forget_everything()


def test_it_is_handed_out_exactly_once() -> None:
    """The whole of "just this once". A value that answered twice would be a
    vault entry with a shorter name for itself."""
    hold("acme/wms.test/password", "hunter2", now=1000.0)

    assert take("acme/wms.test/password", now=1001.0) == "hunter2"
    assert take("acme/wms.test/password", now=1002.0) is None


def test_it_is_forgotten_after_its_quarter_of_an_hour() -> None:
    """A password nobody used is not still in memory at the end of a shift."""
    hold("acme/wms.test/password", "hunter2", now=1000.0)

    assert waiting("acme/wms.test/password", now=1000.0 + K_HELD_FOR - 1) is True
    assert take("acme/wms.test/password", now=1000.0 + K_HELD_FOR + 1) is None


def test_typing_it_again_replaces_the_first() -> None:
    """Somebody who types it twice meant the second one -- they mistyped the
    first, which is the whole reason they are typing it again."""
    hold("acme/wms.test/password", "wrong", now=1000.0)
    hold("acme/wms.test/password", "right", now=1010.0)

    assert take("acme/wms.test/password", now=1011.0) == "right"


def test_one_system_is_not_another() -> None:
    hold("acme/wms.test/password", "hunter2", now=1000.0)

    assert take("acme/other.test/password", now=1001.0) is None
    assert take("acme/wms.test/password", now=1001.0) == "hunter2"


async def test_the_runner_takes_it_before_the_vault_and_only_once() -> None:
    """The lookup a step goes through. A value given for one run beats the
    stored one -- an operator typing a password into the card is answering
    about the run in front of them, not rotating what the deployment keeps --
    and the run after that is back on the vault."""
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from tests.unit.fakes import FakeCredentialVault, FakeUnitOfWork

    vault = FakeCredentialVault()
    await vault.store("acme/wms.test/password", "the-stored-one")
    runs = StartWorkflowRun(
        FakeUnitOfWork(),
        channel=None,  # type: ignore[arg-type]
        asker=None,
        plan_model="m",
        rescue_model="m",
        clock=lambda: 0.0,  # type: ignore[arg-type,return-value]
        cap_usd=1.0,
        stops=None,  # type: ignore[arg-type]
        approvals=None,  # type: ignore[arg-type]
        vault=vault,
    )

    hold("acme/wms.test/password", "typed-just-now")

    assert await runs._secret_for("acme/wms.test/password") == "typed-just-now"
    assert await runs._secret_for("acme/wms.test/password") == "the-stored-one"


async def test_with_no_vault_at_all_a_password_given_once_still_signs_in() -> None:
    """A deployment that keeps no credentials is one somebody can still sign
    into by hand, which is half the point of this door."""
    from sro.application.execution.workflow_runs import StartWorkflowRun
    from tests.unit.fakes import FakeUnitOfWork

    runs = StartWorkflowRun(
        FakeUnitOfWork(),
        channel=None,  # type: ignore[arg-type]
        asker=None,
        plan_model="m",
        rescue_model="m",
        clock=lambda: 0.0,  # type: ignore[arg-type,return-value]
        cap_usd=1.0,
        stops=None,  # type: ignore[arg-type]
        approvals=None,  # type: ignore[arg-type]
    )

    hold("acme/wms.test/password", "typed-just-now")

    assert await runs._secret_for("acme/wms.test/password") == "typed-just-now"
    assert await runs._secret_for("acme/wms.test/password") is None
