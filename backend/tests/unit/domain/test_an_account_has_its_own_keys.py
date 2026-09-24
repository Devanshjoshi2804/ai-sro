from datetime import UTC, datetime, timedelta

import pytest

from sro.domain.execution.account import (
    K_LEASE_TTL,
    K_USERNAME_MAX_LEN,
    Account,
    Lease,
    LeaseState,
)
from sro.domain.shared.errors import InvariantViolation

NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)


def test_two_systems_behind_one_provider_keep_two_passwords() -> None:
    wms = Account.of("greyorange", "https://wms.example/portal", "lena")
    tms = Account.of("greyorange", "https://tms.example/", "lena")

    assert wms.vault_key("password") == "greyorange/wms.example/lena/password"
    assert wms.vault_key("password") != tms.vault_key("password")


def test_two_operators_on_one_system_keep_two_states() -> None:
    lena = Account.of("greyorange", "https://wms.example", "Lena@Example.com")
    omar = Account.of("greyorange", "https://wms.example", "omar@example.com")

    assert lena.vault_key("state") == "greyorange/wms.example/lena%40example%2Ecom/state"
    assert lena.vault_key("state") != omar.vault_key("state")
    assert lena.lock_id != omar.lock_id


def test_the_key_the_panel_stores_is_the_key_the_broker_reads() -> None:
    panel = Account.of("greyorange", "wms.example", "lena")
    broker = Account.of("greyorange", "HTTPS://WMS.example:443/start", "lena")

    assert panel.vault_key("password") == broker.vault_key("password")
    assert panel.vault_key("password") == "greyorange/wms.example/lena/password"


def test_a_schemeless_system_with_a_port_still_normalises() -> None:
    schemeless = Account.of("greyorange", "WMS.example:443", "lena")

    assert schemeless.origin == "wms.example:443"


def test_a_schemeless_system_does_not_leak_its_userinfo_into_the_key() -> None:
    creds = Account.of("greyorange", "bob:hunter2@wms.example", "lena")

    assert creds.origin == "wms.example"
    assert "hunter2" not in creds.vault_key("password")


def test_a_field_that_normalises_to_nothing_is_refused() -> None:
    lena = Account.of("greyorange", "https://wms.example", "lena")

    with pytest.raises(InvariantViolation):
        lena.vault_key("!!!")


def test_a_username_cannot_reach_into_another_key() -> None:
    sly = Account.of("greyorange", "https://wms.example", "a/../b")

    assert sly.vault_key("password").split("/") == [
        "greyorange",
        "wms.example",
        "a%2F%2E%2E%2Fb",
        "password",
    ]


def test_a_blank_username_is_refused_rather_than_a_double_slash_key() -> None:
    with pytest.raises(InvariantViolation):
        Account.of("greyorange", "https://wms.example", "   ")


def test_a_username_past_the_limit_is_refused() -> None:
    with pytest.raises(InvariantViolation):
        Account.of("greyorange", "https://wms.example", "a" * (K_USERNAME_MAX_LEN + 1))


def test_every_field_gets_the_account_scoped_key_the_same_way() -> None:
    lena = Account.of("greyorange", "https://wms.example", "lena")

    assert lena.vault_key("MFA Code") == "greyorange/wms.example/lena/mfa-code"


def test_a_lease_is_live_until_its_heartbeat_runs_out() -> None:
    lease = Lease(
        "lse_1",
        Account.of("t", "https://wms.example", "lena"),
        "http://steel:3000",
        "s1",
        "ctx_1",
        "run_1",
        NOW,
        NOW + K_LEASE_TTL,
        LeaseState.READY,
    )

    assert lease.live(NOW + timedelta(seconds=30))
    assert not lease.live(NOW + K_LEASE_TTL)
