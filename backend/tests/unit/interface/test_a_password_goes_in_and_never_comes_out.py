"""The door that keeps one value for a run to type, and answers with none.

This is the narrowest surface in the system and the one worth the most tests.
An operator asked for their browser to sign in for them; the answer is not to
record the password -- the recorder strikes it out and always will -- but to
keep it once, deliberately, bound to the run it was given for, and fetch it
at the moment that run's step types it.

Properties, and every one of them is a way this could have gone wrong: the
value never comes back, the tenant comes from the credential and never from
the body, a browser's own secret does not open the tenant's vault, the key a
person stores under is the key the run asks for, a run from another tenant is
refused before anything is held, and a secret held for one run is never given
to another.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.domain.execution.secrets import secret_key_of
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.device import AgentDevice
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

WMS = "keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
LAPTOP = DeviceId("dev-lena-laptop")
HERS = "secret-for-dev-lena-laptop"
KEPT = "not-in-any-test-fixture-8f21"
RUN_A = "run_a_8f21"


def _run(run_id: str = RUN_A, *, tenant: TenantId = f.TENANT) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant.value,
        workflow_id="wfl_test",
        device_id=LAPTOP.value,
        values={},
        started_by=f.OPERATOR.value,
        live=True,
        allow_focus=False,
        started_at="2026-03-01T09:00:00+00:00",
    )


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


@pytest.fixture
async def client(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


def _body(**over: object) -> dict[str, object]:
    asked: dict[str, object] = {"system": WMS, "field": "password", "value": KEPT}
    asked.update(over)
    return asked


def _once_body(**over: object) -> dict[str, object]:
    return _body(run_id=RUN_A, **over)


async def test_what_is_kept_is_answered_by_its_key_and_never_by_its_value(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    stored = await client.put("/v1/secrets", json=_body())

    assert stored.status_code == 200, stored.text
    assert stored.json() == {"key": f"{f.TENANT.value}/{WMS}/password"}
    # The whole response, headers included: a value echoed anywhere lands in a
    # browser history, a proxy log and whatever records the call in between.
    assert KEPT not in stored.text
    assert await container.vault.get(f"{f.TENANT.value}/{WMS}/password") == KEPT


async def test_a_password_given_with_its_username_is_kept_for_that_account(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    stored = await client.put("/v1/secrets", json=_body(system=f"https://{WMS}", username="lena"))

    key = f"{f.TENANT.value}/{WMS}/lena/password"
    assert stored.json() == {"key": key}
    assert await container.vault.get(key) == KEPT


async def test_a_non_password_field_with_a_username_still_gets_the_account_key(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    stored = await client.put("/v1/secrets", json=_body(field="One-Time Code", username="lena"))

    key = f"{f.TENANT.value}/{WMS}/lena/one-time-code"
    assert stored.json() == {"key": key}
    assert await container.vault.get(key) == KEPT


async def test_a_blank_username_is_refused_before_the_vault_is_touched(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    refused = await client.put("/v1/secrets", json=_body(username="   "))

    assert refused.status_code == 422
    assert await container.vault.get(f"{f.TENANT.value}/{WMS}/password") is None


async def test_there_is_no_door_that_reads_one_back(client: httpx.AsyncClient) -> None:
    """The property this design rests on. A route that answered with a stored
    value would put every credential in the deployment one leaked tenant token
    away from being read out, which is the whole thing a vault is for."""
    await client.put("/v1/secrets", json=_body())

    assert (await client.get("/v1/secrets")).status_code in (404, 405)
    assert (await client.get(f"/v1/secrets/{f.TENANT.value}/{WMS}/password")).status_code in (
        404,
        405,
    )


async def test_the_vault_it_lands_in_is_the_caller_s_own_and_never_a_named_one(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    """There is no tenant field, and adding one would be a caller choosing
    whose vault to write into. The key is built here from the credential."""
    stored = await client.put("/v1/secrets", json=_body(tenant_id="somebody-else"))

    assert stored.json()["key"].startswith(f"{f.TENANT.value}/")
    assert await container.vault.get(f"somebody-else/{WMS}/password") is None


async def test_a_browser_may_not_write_into_the_tenants_vault(
    client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
) -> None:
    """Tenant-only, and harder than the model budget this rule was written for.
    A browser's secret opens its own doors -- ingest, its socket, the runner's
    -- and not the place every credential in the deployment is kept."""
    uow.devices.rows[LAPTOP.value] = AgentDevice(
        id=LAPTOP,
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        label="lena",
        extension_version="0.1.0",
        registered_at=f.at(0),
        last_seen_at=f.at(0),
        secret=HERS,
    )

    refused = await client.put(
        "/v1/secrets",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": HERS},
        json=_body(),
    )

    assert refused.status_code == 403, refused.text
    assert await container.vault.get(f"{f.TENANT.value}/{WMS}/password") is None


async def test_storing_the_same_key_twice_is_a_rotation_and_not_a_second_credential(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    await client.put("/v1/secrets", json=_body())
    await client.put("/v1/secrets", json=_body(value="the-new-one-3c07"))

    assert await container.vault.get(f"{f.TENANT.value}/{WMS}/password") == "the-new-one-3c07"


async def test_the_key_answered_with_is_the_key_a_run_will_ask_for(
    client: httpx.AsyncClient,
) -> None:
    # Said twice, in two places, because a mismatch here is silent: the value
    # would sit in the vault and the step would refuse as though nothing had
    # ever been stored.
    stored = await client.put("/v1/secrets", json=_body(system=f"https://{WMS}/auth/realms/x"))

    assert stored.json()["key"] == secret_key_of(f.TENANT.value, WMS, "password")


async def test_a_value_with_nothing_in_it_is_refused_before_the_vault_is_touched(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    refused = await client.put("/v1/secrets", json=_body(value=""))

    assert refused.status_code == 422
    assert await container.vault.get(f"{f.TENANT.value}/{WMS}/password") is None


async def test_a_one_run_password_given_with_its_username_is_held_under_the_account_key(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    uow.workflow_runs.rows[RUN_A] = _run()

    held = await client.post(
        "/v1/secrets/once", json=_once_body(system=f"https://{WMS}", username="lena")
    )

    assert held.status_code == 202, held.text
    key = f"{f.TENANT.value}/{WMS}/lena/password"
    assert held.json()["key"] == key
    assert container.one_time_secrets.take(key, run_id=RUN_A) == KEPT


async def test_a_password_given_for_one_run_never_reaches_the_vault(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """ "Just this once" is the other answer to the question this door asks.
    It is held for the run that asked and written nowhere -- so a deployment
    keeps no copy, and there is nothing to rotate or delete."""
    uow.workflow_runs.rows[RUN_A] = _run()

    held = await client.post("/v1/secrets/once", json=_once_body())

    assert held.status_code == 202, held.text
    key = f"{f.TENANT.value}/{WMS}/password"
    assert held.json()["key"] == key
    assert held.json()["until"] > 0
    # The value, nowhere in the answer and nowhere in the vault.
    assert KEPT not in held.text
    assert await container.vault.get(key) is None
    # And it is there for the run that asked, once.
    assert container.one_time_secrets.take(key, run_id=RUN_A) == KEPT
    assert container.one_time_secrets.take(key, run_id=RUN_A) is None


async def test_a_one_run_password_lands_in_the_caller_s_own_key(
    client: httpx.AsyncClient, uow: FakeUnitOfWork
) -> None:
    uow.workflow_runs.rows[RUN_A] = _run()

    held = await client.post("/v1/secrets/once", json=_once_body(tenant_id="somebody-else"))

    assert held.json()["key"].startswith(f"{f.TENANT.value}/")


async def test_a_secret_held_for_one_run_is_not_given_to_another(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """The property the run id exists to buy: a run in the same tenant that
    was not given the password does not get it either."""
    uow.workflow_runs.rows[RUN_A] = _run()

    held = await client.post("/v1/secrets/once", json=_once_body())

    assert held.status_code == 202, held.text
    key = held.json()["key"]
    assert container.one_time_secrets.take(key, run_id="run_b_never_asked") is None
    assert container.one_time_secrets.take(key, run_id=RUN_A) == KEPT


async def test_the_route_rejects_a_run_from_another_tenant(
    client: httpx.AsyncClient, container: _FakeContainer, uow: FakeUnitOfWork
) -> None:
    """A run id is only useful as a binding if it is checked. A run that
    belongs to somebody else's tenant is refused before anything is held --
    the same "no such run" a caller gets for a run id that does not exist at
    all, so a probe learns nothing about who else is running jobs."""
    uow.workflow_runs.rows[RUN_A] = _run(tenant=TenantId("somebody-else"))

    held = await client.post("/v1/secrets/once", json=_once_body())

    assert held.status_code == 404, held.text
    key = f"{f.TENANT.value}/{WMS}/password"
    assert container.one_time_secrets.take(key, run_id=RUN_A) is None


async def test_the_route_rejects_a_run_id_that_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    held = await client.post("/v1/secrets/once", json=_once_body())

    assert held.status_code == 404, held.text
