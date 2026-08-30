"""Reading each demonstration's values back out of its own recorded traffic.

A version stores the two doings it diffed. Every other doing of the task is
cited in its provenance and its traffic is still here, so the values it used
are readable rather than lost -- and reading them is the difference between a
review screen that shows three demonstrations and one that shows ten.

What this must never do is fill a cell it could not read. A value nobody
recorded, sitting in a table headed "what each doing did", is worse than a gap:
a reviewer has no way to tell it apart from a measurement.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.skill.read_doings import values_in
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import Body, CapturedRequest
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.skill import SkillStep, SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f

WMS = "https://wms.acme.test"
AT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


def _version(*, url: str, body: str | None, names: tuple[str, ...]) -> SkillVersion:
    return f.skill_version(
        steps=(
            SkillStep(
                index=0,
                intent="Create the work area",
                network_plan=NetworkPlan(
                    method="POST",
                    url=Template(url),
                    body=Template(body) if body is not None else None,
                    expected_status=200,
                ),
            ),
        ),
        parameters=tuple(Parameter(name=name, kind=ParameterKind.INPUT) for name in names),
    )


def _sent(
    url: str, body: str | None, *, method: str = "POST", status: int = 200
) -> tuple[ActionFrame, ...]:
    return (
        f.frame(
            requests=(
                CapturedRequest(
                    request_id="r1",
                    method=method,
                    url=url,
                    resource_type="xhr",
                    started_at=AT + timedelta(seconds=1),
                    status=status,
                    request_body=Body(text=body) if body is not None else None,
                ),
            ),
        ),
    )


def test_a_doing_nobody_diffed_still_says_what_it_filled_in() -> None:
    # The whole point: this recording was read only for what was left empty,
    # and its values were never stored on the version. They are still here.
    version = _version(
        url=f"{WMS}/api/work-areas",
        body='{"name":"$work_area","description":"$work_area_description"}',
        names=("work_area", "work_area_description"),
    )

    read = values_in(
        version,
        _sent(f"{WMS}/api/work-areas", '{"name":"NEWTESTS","description":"the first one"}'),
    )

    assert read == {"work_area": "NEWTESTS", "work_area_description": "the first one"}


def test_a_field_this_doing_sent_holding_nothing_reads_as_left_empty() -> None:
    # Not as the four characters `null`: "this doing left it out" is the fact
    # behind every optional field, and it is what a reviewer is looking for.
    version = _version(
        url=f"{WMS}/api/work-areas",
        body='{"name":"$work_area","priority":$absolute_priority}',
        names=("work_area", "absolute_priority"),
    )

    read = values_in(version, _sent(f"{WMS}/api/work-areas", '{"name":"NEWTESTS","priority":null}'))

    assert read == {"work_area": "NEWTESTS", "absolute_priority": None}


def test_two_slots_in_one_body_do_not_swallow_each_other() -> None:
    version = _version(
        url=f"{WMS}/api/work-areas",
        body='{"a":"$one","b":"$two"}',
        names=("one", "two"),
    )

    read = values_in(version, _sent(f"{WMS}/api/work-areas", '{"a":"X","b":"Y"}'))

    assert read == {"one": "X", "two": "Y"}


def test_two_slots_with_nothing_between_them_take_the_shortest_reading() -> None:
    # Genuine ambiguity: `$a/$b` fits `x/y/z` two ways, and neither is more
    # true than the other. Pinned rather than left to whichever way the regex
    # engine happens to lean, so the same evidence reads the same next year.
    version = _version(url=f"{WMS}/api/$a/$b", body=None, names=("a", "b"))

    read = values_in(version, _sent(f"{WMS}/api/x/y/z", None))

    assert read == {"a": "x", "b": "y/z"}


def test_a_value_in_the_url_is_read_the_same_way() -> None:
    version = _version(
        url=f"{WMS}/api/work-areas/$work_area/priority",
        body=None,
        names=("work_area",),
    )

    read = values_in(version, _sent(f"{WMS}/api/work-areas/SROTEST1/priority", None))

    assert read == {"work_area": "SROTEST1"}


def test_a_doing_that_sent_something_else_reads_as_nothing_rather_than_as_a_value() -> None:
    # The refusal this exists for. This doing called a different endpoint, so
    # there is no measurement to report -- and an empty mapping is how the
    # screen learns to say "this doing does not answer for that field".
    version = _version(
        url=f"{WMS}/api/work-areas",
        body='{"name":"$work_area"}',
        names=("work_area",),
    )

    read = values_in(version, _sent(f"{WMS}/api/suppliers", '{"name":"ACME"}'))

    assert read == {}


def test_a_body_that_changed_shape_still_yields_what_the_url_names() -> None:
    # The endpoint moved its payload around between doings. Which record was
    # acted on is still legible, and losing that too would be a gap this does
    # not have to have.
    version = _version(
        url=f"{WMS}/api/work-areas/$work_area",
        body='{"description":"$work_area_description"}',
        names=("work_area", "work_area_description"),
    )

    read = values_in(
        version, _sent(f"{WMS}/api/work-areas/SROTEST2", '{"attributes":{"desc":"moved"}}')
    )

    assert read == {"work_area": "SROTEST2"}


def test_a_write_the_system_refused_is_not_read_as_what_the_doing_did() -> None:
    # The operator typed it and the warehouse rejected it. Reporting that
    # value as what this doing filled in would show a reviewer a work area
    # that never existed.
    version = _version(
        url=f"{WMS}/api/work-areas",
        body='{"name":"$work_area"}',
        names=("work_area",),
    )

    read = values_in(version, _sent(f"{WMS}/api/work-areas", '{"name":"REJECTED"}', status=500))

    assert read == {}
