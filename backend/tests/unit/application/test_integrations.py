from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.integrations.connect import ConnectSession
from sro.application.integrations.end_user import end_user_id
from sro.application.integrations.listing import ListIntegrations
from sro.application.ports.nango import NangoUnavailable
from sro.domain.shared.errors import Conflict, InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests.unit.fakes import FakeCredentialVault

CTX = RequestContext(TenantId("acme"), PrincipalId("lena"))


async def test_a_refused_integration_never_reaches_nango() -> None:
    with pytest.raises(Conflict):
        await ConnectSession(None, ("microsoft",), "", "").execute(CTX, integration="slack")


async def test_without_nango_a_configured_integration_is_unavailable() -> None:
    with pytest.raises(NangoUnavailable):
        await ListIntegrations(None, ("microsoft",), FakeCredentialVault(), None).execute(CTX)
    assert await ListIntegrations(None, (), FakeCredentialVault(), None).execute(CTX) == []


def test_the_end_user_id_cannot_collide_across_tenants() -> None:
    assert end_user_id(CTX) == "acme:lena"
    for tenant, principal in (("a:b", "c"), ("a", "b:c")):
        with pytest.raises(InvariantViolation):
            end_user_id(RequestContext(TenantId(tenant), PrincipalId(principal)))
