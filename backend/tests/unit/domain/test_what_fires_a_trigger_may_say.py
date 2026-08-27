"""What a message that fires a trigger is allowed to change.

A trigger is a button with its arguments already filled in, and that is what
makes a schedule safe: the same task, on the same thing, every morning. A
message names a different thing each time -- the order number in a mail -- so
some of the values have to come from whatever fired it.

Which ones is the whole question. A relay that could name any parameter could
name the facility, and the read somebody authorised for DC01 answers about
another warehouse.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, SkillId
from sro.domain.trigger.trigger import Trigger, TriggerId, TriggerKind
from tests import factories as f


def _trigger(**over: object) -> Trigger:
    defaults: dict[str, object] = {
        "id": TriggerId("trg-1"),
        "tenant_id": f.TENANT,
        "skill_id": SkillId("skl-1"),
        "kind": TriggerKind.INBOUND,
        "created_by": PrincipalId("devansh"),
        "created_at": datetime(2026, 8, 26, tzinfo=UTC),
        "parameters": {"facility": "DC01"},
        "inbound_token": "a-secret",
        "from_message": ("order_id",),
    }
    return Trigger(**{**defaults, **over})  # type: ignore[arg-type]


def test_the_message_fills_the_names_it_was_told_it_could() -> None:
    values = _trigger().values_from({"order_id": "4471"})

    assert values == {"facility": "DC01", "order_id": "4471"}


def test_a_name_it_was_not_told_about_changes_nothing() -> None:
    """The line this exists for. A relay posting `facility=OTHER_DC` would
    otherwise redirect a read at a warehouse nobody authorised."""
    values = _trigger().values_from({"order_id": "4471", "facility": "OTHER_DC"})

    assert values["facility"] == "DC01"


def test_an_unknown_field_does_not_stop_a_working_mailbox_rule() -> None:
    """Dropped rather than refused: a relay that adds a field to its payload is
    not a reason for a rule that has worked for a year to stop."""
    values = _trigger().values_from({"order_id": "4471", "message_id": "<abc@mail>"})

    assert values == {"facility": "DC01", "order_id": "4471"}


def test_a_trigger_told_nothing_runs_on_what_it_was_created_with() -> None:
    assert _trigger(from_message=()).values_from({"order_id": "4471"}) == {"facility": "DC01"}


def test_only_an_inbound_trigger_is_told_anything() -> None:
    """A schedule fires at three in the morning with nobody to hear it name
    something new. Refused at creation, where somebody is reading."""
    with pytest.raises(InvariantViolation, match="only an inbound one is told anything"):
        _trigger(kind=TriggerKind.MANUAL, inbound_token=None, cron=None)
