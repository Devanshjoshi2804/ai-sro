"""Which page in the operator's browser a run is entitled to act on.

A device is a whole Chrome, not a page. The system a skill was taught on is
read off what the demonstration recorded, and it travels with every command --
otherwise the extension can only take whatever is frontmost, and the difference
between the WMS and somebody's inbox is a coin toss made on their behalf.
"""

from __future__ import annotations

from sro.application.execution.execute_skill import ExecuteStep, _origin_of
from sro.domain.execution.run import Run, RunId
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from tests import factories
from tests.unit import fakes


def _version(*urls: str | None) -> object:
    steps = tuple(
        factories.step(
            index=index,
            network_plan=None
            if url is None
            else NetworkPlan(method="POST", url=Template(url), expected_status=200),
        )
        for index, url in enumerate(urls)
    )
    # Declared because a version refuses to hold a step naming a parameter it
    # does not have -- the same rule that keeps a plan from referring to values
    # no run could supply.
    return factories.skill_version(
        steps=steps,
        parameters=(
            factories.parameter(name="wave_id"),
            factories.parameter(name="facility"),
        ),
    )


def test_the_origin_is_read_off_the_first_recorded_call() -> None:
    version = _version("https://wms.example/api/waves/$wave_id/release")
    assert _origin_of(version) == "https://wms.example"


def test_a_step_with_no_call_is_stepped_over_rather_than_giving_up() -> None:
    """A skill often opens with a click and only then makes a request. Reading
    only the first step would leave those skills guessing."""
    version = _version(None, "https://wms.example:8443/api/waves")
    assert _origin_of(version) == "https://wms.example:8443"


def test_a_parameterised_host_is_no_answer_at_all() -> None:
    """The placeholder is not filled in until the step runs, and a tab cannot
    be chosen by a template. Better to fall back to the visible page than to
    ask the browser for a tab on `https://$facility.wms.example`."""
    version = _version("https://$facility.wms.example/api/waves")
    assert _origin_of(version) is None


def test_a_skill_taught_only_through_the_interface_has_no_origin() -> None:
    assert _origin_of(_version(None, None)) is None
    assert _origin_of(None) is None


async def test_the_browser_is_told_both_the_page_and_whether_it_may_be_shown() -> None:
    """What the run knows reaches the browser as one pair of facts: which tab,
    and whether it may be brought to the front. Neither is the browser's to
    decide -- it has no way to know which of a dozen tabs is the WMS, and no
    business deciding whether to interrupt the person in front of it."""
    agents = fakes.FakeAgentDrivers()
    executor = ExecuteStep(
        fakes.FakeUnitOfWork(),
        fakes.FakeHttpCaller(),
        fakes.FakeCredentialVault(),
        agents=agents,
    )
    run = Run(
        id=RunId("run-1"),
        tenant_id=factories.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=factories.OPERATOR,
        started_at=factories.at(800),
        # Named, because an assisted run that changes the system refuses to
        # exist without a human on the record for it.
        authorized_by=factories.OPERATOR,
        device_id=DeviceId("dev-1"),
        may_take_focus=True,
    )
    version = _version("https://wms.example/api/waves")

    assert executor._ui_for(run, version) is agents.driver
    assert agents.told == ("https://wms.example", True)


def test_a_step_acts_on_its_own_system_rather_than_the_skill_s() -> None:
    """A workflow's steps do not all belong to the same system.

    Bound to one origin for the whole run, the second half would be attempted in
    the first half's tab: the extension picks a tab by the origin it is handed,
    so an ERP step would look for its control on a WMS page and report that the
    control had moved.
    """
    version = _version("https://wms.example/api/waves", "https://erp.example/api/receipts")

    assert _origin_of(version, version.steps[0]) == "https://wms.example"
    assert _origin_of(version, version.steps[1]) == "https://erp.example"


def test_a_step_with_no_call_of_its_own_falls_back_to_the_skill_s() -> None:
    """A UI-only step records no URL, and a parameterised host is not one a tab
    can be chosen by. Both borrow the version's answer rather than guessing."""
    version = _version("https://wms.example/api/waves", None)

    assert _origin_of(version, version.steps[1]) == "https://wms.example"

    parameterised = _version("https://wms.example/api/waves", "https://$facility.erp.example/x")
    assert _origin_of(parameterised, parameterised.steps[1]) == "https://wms.example"
