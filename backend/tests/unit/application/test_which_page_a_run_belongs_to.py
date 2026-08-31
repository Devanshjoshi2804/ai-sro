"""Which page in the operator's browser a run is entitled to act on.

A device is a whole Chrome, not a page. The system a skill was taught on is
read off what the demonstration recorded, and it travels with every command --
otherwise the extension can only take whatever is frontmost, and the difference
between the WMS and somebody's inbox is a coin toss made on their behalf.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.execution.execute_skill import ExecuteStep, _origin_of
from sro.domain.connection.connection import Connection, ConnectionId
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


def _connection(system: str, base_url: str) -> Connection:
    connection = Connection(
        id=ConnectionId(f"con-{system}"),
        tenant_id=factories.TENANT,
        name=system,
        target_system=system,
        base_url=base_url,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    connection.authenticated(datetime(2026, 1, 2, tzinfo=UTC))
    return connection


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


def test_the_browser_is_told_what_to_say_on_the_page_it_is_driving() -> None:
    """The page being driven has to be able to say so.

    The panel already shows a run performing, with the step count and a button
    to stop it. Nobody looks at the panel: they are looking at their own screen
    watching fields fill and buttons press, and nothing there distinguishes that
    from a colleague on the same account or the application misbehaving. So the
    tab says it itself -- and it can only say what the driver was told, which is
    why this travels with the command rather than being assembled in the worker.

    The step's intent rather than the skill's name: somebody watching their own
    screen change is asking what is happening to it now.
    """
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
        authorized_by=factories.OPERATOR,
        device_id=DeviceId("dev-1"),
    )
    version = _version("https://wms.example/api/waves", None, None)

    executor._ui_for(run, version, version.steps[1])

    # Counted from one, because the band is read by a person and step 0 of 3 is
    # not a sentence anybody says.
    assert agents.named == (version.steps[1].intent, 2, 3)


def test_a_step_nobody_named_still_drives_rather_than_refusing() -> None:
    """The band is a courtesy and the run is the point.

    Without a step -- the vision rung asking for a driver before it knows which
    gesture it will propose -- there is nothing to name, and the page falls back
    to saying only that it is being driven. A run that failed because it could
    not compose a sentence would be a worse trade than a vaguer band.
    """
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
        authorized_by=factories.OPERATOR,
        device_id=DeviceId("dev-1"),
    )

    assert executor._ui_for(run, None, None) is agents.driver
    assert agents.named == ("", None, None)


def test_a_skill_taught_only_by_clicking_is_placed_by_the_system_it_belongs_to() -> None:
    """The commonest kind of skill recorded no call at all.

    A task demonstrated entirely by clicking -- and every task on a screen that
    renders itself from a bundle rather than fetching as it goes -- names no URL
    on any step, so it had no origin, so the extension drove whichever tab
    happened to be in front. That reads back as every step reporting
    `control_not_found`, which sends somebody to re-teach a skill that was never
    wrong: it was performed on the wrong page.

    Nothing here is inferred. The version already records which systems it
    touched, and the connection already records the host the operator
    authenticated to.
    """
    version = factories.skill_version(
        # No call on any step, which is what "taught by clicking" means.
        steps=(
            factories.step(index=0, network_plan=None),
            factories.step(index=1, network_plan=None),
        ),
        systems=("blue_yonder",),
    )
    connections = [
        _connection("erp", "https://erp.example/portal"),
        _connection("blue_yonder", "https://wms.example/portal?siteId=SG#wm.config"),
    ]

    # The path and the query go: a tab is chosen by origin, and the deep link
    # the operator happened to connect through is not where the skill acts.
    assert _origin_of(version, version.steps[0], connections) == "https://wms.example"


def test_two_systems_and_no_recorded_call_is_still_no_answer() -> None:
    """Picking either would send half the run to the wrong tab.

    A workflow crosses systems by definition, so one origin cannot be right for
    all of it -- and a wrong origin is worse than none, because none falls back
    to the page the operator is actually looking at, which is at least honestly
    a guess rather than a confident wrong one.
    """
    version = factories.skill_version(
        steps=(factories.step(index=0, network_plan=None),),
        systems=("blue_yonder", "erp"),
    )
    connections = [
        _connection("blue_yonder", "https://wms.example/portal"),
        _connection("erp", "https://erp.example/portal"),
    ]

    assert _origin_of(version, version.steps[0], connections) is None


def test_a_recorded_call_still_wins_over_the_connection() -> None:
    """What the demonstration did beats what the tenant configured. A connection
    is a base URL somebody typed once; a recorded call is where the task was
    actually performed, and the two disagree the moment a system is reached
    through more than one host."""
    version = factories.skill_version(
        steps=(
            factories.step(
                index=0,
                network_plan=NetworkPlan(
                    method="POST", url=Template("https://real.example/api"), expected_status=200
                ),
            ),
        ),
        systems=("blue_yonder",),
    )

    assert (
        _origin_of(version, version.steps[0], [_connection("blue_yonder", "https://wms.example/x")])
        == "https://real.example"
    )


def test_the_browser_is_told_which_screen_to_be_on() -> None:
    """The origin gets the run to the right system; the screen gets it to the
    right page of that system.

    Both are needed and neither substitutes: an operator's Chrome has a dozen
    tabs and one of them is the WMS, and the WMS itself has a hundred screens of
    which the task was demonstrated on exactly one. Told only the origin, a run
    performed on whichever WMS page happened to be open -- and reported a page
    of `control_not_found` that said nothing about being on the wrong screen.
    """
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
        authorized_by=factories.OPERATOR,
        device_id=DeviceId("dev-1"),
    )
    taught_on = "https://wms.example/portal#wm.config/wm.config.work.work.areas"
    version = factories.skill_version(
        steps=(factories.step(index=0, network_plan=None),),
        starts_on=taught_on,
    )

    executor._ui_for(run, version, version.steps[0])

    assert agents.sent_to == taught_on


def test_a_skill_that_recorded_no_screen_says_so_rather_than_inventing_one() -> None:
    """Everything taught before the recorder kept the page has none, and a run
    of one of those still has to work: it acts where the operator already is,
    which is what it did before any of this existed."""
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
        authorized_by=factories.OPERATOR,
        device_id=DeviceId("dev-1"),
    )

    executor._ui_for(run, _version("https://wms.example/api/waves"), None)

    assert agents.sent_to is None
