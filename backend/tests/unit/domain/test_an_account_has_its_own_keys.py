from datetime import UTC, datetime, timedelta

from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState

NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)


def test_two_systems_behind_one_provider_keep_two_passwords() -> None:
    wms = Account.of("greyorange", "https://wms.example/portal", "lena")
    tms = Account.of("greyorange", "https://tms.example/", "lena")

    assert wms.vault_key("password") == "greyorange/https://wms.example/lena/password"
    assert wms.vault_key("password") != tms.vault_key("password")


def test_two_operators_on_one_system_keep_two_states() -> None:
    lena = Account.of("greyorange", "https://wms.example", "Lena@Example.com")
    omar = Account.of("greyorange", "https://wms.example", "omar@example.com")

    assert lena.vault_key("state") == "greyorange/https://wms.example/lena@example.com/state"
    assert lena.vault_key("state") != omar.vault_key("state")
    assert lena.lock_id != omar.lock_id


def test_a_username_cannot_reach_into_another_key() -> None:
    sly = Account.of("greyorange", "https://wms.example", "a/../b")

    assert "/../" not in sly.vault_key("password")


def test_a_lease_is_live_until_its_heartbeat_runs_out() -> None:
    lease = Lease(
        "lse_1",
        Account.of("t", "https://wms.example", "lena"),
        "http://steel:3000",
        "s1",
        "run_1",
        NOW,
        NOW + K_LEASE_TTL,
        LeaseState.READY,
    )

    assert lease.live(NOW + timedelta(seconds=30))
    assert not lease.live(NOW + K_LEASE_TTL)
