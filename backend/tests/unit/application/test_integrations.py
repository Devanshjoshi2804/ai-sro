from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.integrations.connect import ConnectSession
from sro.application.integrations.listing import ListIntegrations
from sro.application.ports.nango import NangoUnavailable
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId, TenantId

CTX = RequestContext(TenantId("acme"), PrincipalId("lena"))


async def test_a_refused_integration_never_reaches_nango() -> None:
    with pytest.raises(Conflict):
        await ConnectSession(None, ("microsoft",), "", "").execute(CTX, integration="slack")


async def test_without_nango_a_configured_integration_is_unavailable() -> None:
    with pytest.raises(NangoUnavailable):
        await ListIntegrations(None, ("microsoft",)).execute(CTX)
    assert await ListIntegrations(None, ()).execute(CTX) == []
