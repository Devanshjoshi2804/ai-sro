"""What separates a step of a task from a fumble.

Neither intersection nor union survives a thousand doings. Intersection is what
induction does today and loses every optional field. Union would learn the task
plus a thousand accidents -- every mis-click, every field somebody typed and
corrected, every interruption.

Frequency is the signal neither has. And frequency alone is not enough: a step
in three per cent of doings that appears whenever one particular value was
supplied is a branch, and dropping it is how a skill silently stops handling the
case somebody needed it for. A step in three per cent with nothing explaining it
is a fumble.
"""

from __future__ import annotations

import pytest

from sro.application.induction import frequency
from sro.application.induction.diff import Alignment, Parameterisation, Substitution
from sro.application.induction.frequency import PART_OF_THE_TASK, Standing, standing_of
from sro.application.induction.sites import ActionValueSite, JsonBodySite
from sro.domain.skill.parameter import Parameter, ParameterKind
from tests import factories as f


def _alignment(*counts: int) -> Alignment:
    """A task's steps, given as how many doings contained each one.

    The frames themselves are stand-ins: what decides a step's standing is the
    count beside it and the parameterisation, and building four plausible
    gestures here would only invite a reader to look for the answer in them.
    """
    return Alignment(
        reference=tuple(f.frame(index) for index in range(len(counts))),
        seen=dict(enumerate(counts)),
    )


NOTHING_EXPLAINS_IT = Parameterisation(parameters=(), substitutions={})
"""A parameterisation in which no step's keystroke fills an optional field --
so every rare step here is rare for no reason anybody recorded."""


def _fills_an_optional_field(step: int, field: str = "cod_address_id") -> Parameterisation:
    """The one shape that makes a rare step a branch: a keystroke at that step
    typing into a field some doing left empty.

    `absent_as` is what makes the parameter optional -- `Parameter.optional`
    reads it and nothing else -- and `ActionValueSite` is what makes this the
    typing rather than the write that carries the value afterwards.
    """
    return Parameterisation(
        parameters=(Parameter(name=field, kind=ParameterKind.INPUT, absent_as="null"),),
        substitutions={step: (Substitution(site=ActionValueSite(), parameter=field),)},
    )


def test_a_step_every_doing_made_is_always() -> None:
    found = standing_of(_alignment(4, 4, 4), NOTHING_EXPLAINS_IT)

    assert found == {0: Standing.ALWAYS, 1: Standing.ALWAYS, 2: Standing.ALWAYS}


def test_a_step_most_doings_made_is_always() -> None:
    """Three of four. Not unanimous, and not in question either: one operator
    skipping a field once is not evidence that the task does without it."""
    found = standing_of(_alignment(4, 3), NOTHING_EXPLAINS_IT)

    assert found[1] is Standing.ALWAYS


def test_a_rare_step_that_tracks_a_supplied_value_is_a_branch() -> None:
    """The address lookup, at the rate a real branch actually runs at. One
    doing in a hundred contained it, and every one of those was a doing where
    somebody supplied the address -- which is not what noise looks like. A
    branch taken once in a hundred times is still part of the task, and a
    skill that drops it stops handling the case somebody needed it for.
    """
    found = standing_of(_alignment(100, 1), _fills_an_optional_field(1))

    assert found[1] is Standing.CONDITIONAL


def test_a_rare_step_with_nothing_explaining_it_is_noise() -> None:
    """The same count, the same everything, minus the value behind it. This is
    the pair that makes the rule mean something: rarity alone decides nothing,
    and what separates the branch above from the fumble here is only whether a
    supplied parameter explains when it happens."""
    found = standing_of(_alignment(100, 1), NOTHING_EXPLAINS_IT)

    assert found[1] is Standing.NOISE


def test_a_step_whose_write_carries_the_value_is_not_a_branch() -> None:
    """A parameter is not a licence. The keystroke that types an optional
    field only happens when somebody supplies it; the write that carries the
    field goes out either way, carrying the absent form -- so a rare write is
    a fumble however many parameters it substitutes. Reading "this step
    mentions an optional parameter" instead of "this step types it" would
    keep every rare call that happened to send a nullable field.
    """
    carries_it = Parameterisation(
        parameters=(Parameter(name="cod_address_id", kind=ParameterKind.INPUT, absent_as="null"),),
        substitutions={
            1: (Substitution(site=JsonBodySite("/codAddressId"), parameter="cod_address_id"),)
        },
    )

    found = standing_of(_alignment(100, 1), carries_it)

    assert found[1] is Standing.NOISE


def test_a_rare_step_typing_a_required_field_is_noise() -> None:
    """Required, so no doing was ever seen without it, so nothing about this
    step's rarity is explained by whether the value was supplied -- it always
    was. Only an *optional* parameter can account for a step happening
    sometimes."""
    required = Parameterisation(
        parameters=(Parameter(name="carrier_code", kind=ParameterKind.INPUT),),
        substitutions={1: (Substitution(site=ActionValueSite(), parameter="carrier_code"),)},
    )

    found = standing_of(_alignment(100, 1), required)

    assert found[1] is Standing.NOISE


def test_one_demonstration_makes_every_step_always() -> None:
    """There is nothing to disagree with it. Every step of the only doing there
    is was in every doing there is, and a rule that made a lone demonstration's
    steps rare would refuse to learn anything from a task done once."""
    found = standing_of(_alignment(1, 1, 1, 1), _fills_an_optional_field(2))

    assert set(found.values()) == {Standing.ALWAYS}


def test_the_threshold_is_a_share_not_a_count() -> None:
    """The same three-in-four at four doings and at four thousand. A count
    would make the rule mean something different every week as a task is done
    more often -- a step in three doings is the task at four and a rounding
    error at four thousand."""
    assert standing_of(_alignment(4, 3), NOTHING_EXPLAINS_IT)[1] is Standing.ALWAYS
    assert standing_of(_alignment(4000, 3000), NOTHING_EXPLAINS_IT)[1] is Standing.ALWAYS
    assert standing_of(_alignment(4, 1), NOTHING_EXPLAINS_IT)[1] is Standing.NOISE
    assert standing_of(_alignment(4000, 1000), NOTHING_EXPLAINS_IT)[1] is Standing.NOISE


def test_the_threshold_is_read_from_the_named_constant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Not a literal at the call site and not a default argument frozen at
    import. Whoever comes to move this number moves `PART_OF_THE_TASK`, and if
    the decision is spelled out anywhere else it will move without them.
    """
    assert 0 < PART_OF_THE_TASK <= 1

    monkeypatch.setattr(frequency, "PART_OF_THE_TASK", 0.9)
    assert standing_of(_alignment(4, 3), NOTHING_EXPLAINS_IT)[1] is Standing.NOISE

    monkeypatch.setattr(frequency, "PART_OF_THE_TASK", 0.1)
    assert standing_of(_alignment(4, 1), NOTHING_EXPLAINS_IT)[1] is Standing.ALWAYS
