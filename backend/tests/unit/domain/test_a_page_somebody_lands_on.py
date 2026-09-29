"""The rule an operator makes by standing somewhere and saying "do this here".

What is held here is the narrowness. A rule that matched a host would fire on
every page of a warehouse; one that matched a whole url would fire once and
never again, because the url an operator arrives at carries the visit's own
parameters. Between those two is one page, and that is the only useful thing
this can be.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, TriggerId
from sro.domain.trigger.arrival import MAX_PAGE, Arrival, page_of
from sro.domain.trigger.trigger import Trigger, TriggerKind
from tests import factories as f

WMS = "bf56-kms-wms-web-np2.jdadelivers.com"
THE_PAGE = f"{WMS}/portal/page"


def _trigger(**over: object) -> Trigger:
    asked: dict[str, object] = {
        "id": TriggerId("trg-1"),
        "tenant_id": f.TENANT,
        "workflow_id": "wfl_1",
        "kind": TriggerKind.ARRIVAL,
        "created_by": f.OPERATOR,
        "created_at": datetime(2026, 9, 14, tzinfo=UTC),
        "arrival": Arrival(page=THE_PAGE),
        "device_id": DeviceId("dev-lena-laptop"),
    }
    asked.update(over)
    return Trigger(**asked)


def test_the_page_an_operator_is_standing_on_fires_it() -> None:
    assert Arrival(page=THE_PAGE).matches(f"https://{WMS}/portal/page?siteId=SG#top")


CUSTOMER_TYPES = f"https://{WMS}/portal?siteId=SG#wm.config/wm.config.partners.customers.types////"
TRANSPORT = f"https://{WMS}/portal?siteId=SG#wm.config/wm.config.equipment.equipment.transportequipmenttype////"


def test_a_rule_made_on_one_blue_yonder_screen_is_about_that_screen_alone() -> None:
    """Blue Yonder routes on the fragment: every config screen is `/portal`.
    A rule that dropped the route was a rule about every screen of the portal,
    so the fragment's route is part of the page and the rest of it is not."""
    rule = Arrival(page=page_of(CUSTOMER_TYPES))

    assert rule.page == f"{WMS}/portal#wm.config/wm.config.partners.customers.types"
    assert rule.matches(CUSTOMER_TYPES)
    assert not rule.matches(TRANSPORT)
    assert not rule.matches(f"https://{WMS}/portal?siteId=SG")


def test_a_deeper_page_is_a_different_screen() -> None:
    """Exact and never a prefix. A prefix on `host/` is every page on that
    host, which is the interruption this design exists to refuse."""
    assert not Arrival(page=WMS).matches(f"https://{WMS}/portal/page")
    assert not Arrival(page=THE_PAGE).matches(f"https://{WMS}/portal/page/suppliers")


@pytest.mark.parametrize(
    "written",
    [
        f"https://{WMS}/portal/page",
        f"{WMS}/portal/page?siteId=SG",
        f"{WMS}/portal/page#top",
        f"{WMS}/cb#access_token=eyj.eyj.sig",
    ],
    ids=["a scheme", "a query", "a fragment that is no route", "a token in the fragment"],
)
def test_a_url_somebody_pasted_is_refused_rather_than_quietly_trimmed(written: str) -> None:
    # Trimmed here, the rule and the page it was made from would be two strings
    # that have to be kept in step. `page_of` is the one place that trims.
    with pytest.raises(InvariantViolation, match=r"host/path|lowercase"):
        Arrival(page=written)


def test_a_rule_with_no_page_fires_on_every_page_there_is() -> None:
    with pytest.raises(InvariantViolation, match="every page"):
        Arrival(page="   ")


def test_a_page_rule_is_bounded() -> None:
    with pytest.raises(InvariantViolation, match="at most"):
        Arrival(page=f"{WMS}/" + "x" * MAX_PAGE)


@pytest.mark.parametrize(
    ("url", "page"),
    [
        (f"https://{WMS}/portal/page?siteId=SG#wm.config////", f"{WMS}/portal/page#wm.config"),
        (f"https://{WMS}/portal/page#top", f"{WMS}/portal/page"),
        (f"https://{WMS}/cb#access_token=eyJ.eyJ.sig&token_type=Bearer", f"{WMS}/cb"),
        (f"HTTPS://{WMS.upper()}/Portal/Page", f"{WMS}/portal/page"),
        (f"https://{WMS}/portal/page/", f"{WMS}/portal/page"),
        ("http://localhost:3000/needs", "localhost:3000/needs"),
        (f"{WMS}/portal", f"{WMS}/portal"),
        ("chrome://settings", ""),
    ],
    ids=[
        "query and route",
        "a fragment no route",
        "an oauth fragment",
        "case",
        "trailing slash",
        "a port",
        "no scheme",
        "not a page",
    ],
)
def test_a_url_as_the_page_it_is(url: str, page: str) -> None:
    """The port stays: an API on 8000 beside a console on 3000 is the ordinary
    shape of this deployment, and `hosts.origin_of` keeps it for that reason."""
    assert page_of(url) == page


def test_an_arrival_with_no_browser_sees_nobody_arrive() -> None:
    with pytest.raises(InvariantViolation, match="no browser"):
        _trigger(device_id=None)


def test_an_arrival_with_no_page_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="needs a page"):
        _trigger(arrival=None)


def test_only_an_arrival_trigger_carries_a_page() -> None:
    # The same rule `watch` is under: a field that means nothing for this kind
    # is a field somebody will one day read as though it meant something.
    with pytest.raises(InvariantViolation, match="no page to arrive on"):
        _trigger(kind=TriggerKind.MANUAL)


def test_an_arrival_runs_a_job_like_any_other_trigger() -> None:
    made = _trigger()

    assert made.kind is TriggerKind.ARRIVAL
    assert made.workflow_id == "wfl_1"
    assert made.arrival is not None and made.arrival.matches(f"https://{WMS}/portal/page")
