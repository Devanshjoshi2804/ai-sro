"""Nobody types an address id, and nobody types the address either.

The field was a dropdown on the screen, filled by a call this recording
captured. Replaying the id writes to one address forever; asking an operator to
type the street back from memory is asking them to reproduce what the form
would have handed them. So the field stays a dropdown, and the skill carries
where its options come from.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlsplit

import pytest

from sro.application.execution.choices import _searched
from sro.application.induction import lookups
from sro.application.induction.diff import align, parameterise
from sro.application.induction.sites import as_a_filter
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.skill.lookup import Options
from tests import factories as f

ADDRESSES = "https://wms.test/data/WM/wm/addresses"
LIST = f"{ADDRESSES}?siteId=SG"

RECORDS = [
    {"addressId": "A1", "addressName": "APPLIANCE HAUS", "city": "RICHMOND HILL"},
    {"addressId": "A2", "addressName": "OTHER PLACE", "city": "RICHMOND HILL"},
]


def _screen() -> ActionFrame:
    return f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Address")),
        requests=(
            f.request(
                method="GET",
                url=LIST,
                status=200,
                response_body=Body(text=json.dumps({"data": RECORDS})),
            ),
        ),
    )


def _picked() -> ActionFrame:
    """The click alignment drops as exploration -- and the best evidence there
    is about how a person picks this record."""
    return f.frame(
        index=1,
        action=InputAction(
            kind=ActionKind.CLICK,
            target=f.fingerprint(accessible_name="APPLIANCE  HAUS", text="APPLIANCE  HAUS"),
        ),
        requests=(),
    )


def _save(supplier: str) -> ActionFrame:
    return f.frame(
        index=2,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="PUT",
                url=f"{ADDRESSES}/A1",
                status=200,
                request_body=Body(
                    text=json.dumps(
                        {
                            "addressId": "A1",
                            "addressName": "APPLIANCE HAUS",
                            "city": "RICHMOND HILL",
                            "supplierNumber": supplier,
                        }
                    )
                ),
            ),
        ),
    )


def _planned() -> tuple[lookups.PlannedLookup, ...]:
    run_a = (_screen(), _picked(), _save("SUP1"))
    run_b = (_screen(), _picked(), _save("SUP2"))
    pairs = align(run_a, run_b)
    result = parameterise(run_a, run_b)
    return lookups.plan(
        tuple(
            lookups.Wanted(field=c.field, values=(c.value,), step_index=c.step_index)
            for c in result.choices
        ),
        tuple(pair[0] for pair in pairs),
        tuple(pair[1] for pair in pairs),
        screens=run_a,
    )


def test_the_id_carries_the_list_it_was_chosen_from() -> None:
    planned = _planned()

    assert len(planned) == 1
    options = planned[0].options
    assert options.url == LIST
    assert options.value == "addressId"
    # What the operator was seen clicking comes first: it is how they searched.
    assert options.label[0] == "addressName"
    assert options.search == "addressName"


def test_the_field_the_operator_read_is_shown_before_the_rest() -> None:
    assert _planned()[0].shown.startswith("APPLIANCE HAUS")


def test_the_search_is_rewritten_to_look_for_what_is_being_asked_for() -> None:
    """The demonstration searched for what its operator wanted. Replaying that
    searches the wrong ten rows of three hundred thousand."""
    demonstrated = (
        "https://wms.test/wm/addresses?query=%5B%7B%22column%22%3A%22addressName%22%2C"
        "%22operator%22%3A%22EQ%22%2C%22value%22%3A%22%2Ah%2A%22%7D%5D&offset=20&limit=10&siteId=SG"
    )

    rewritten = as_a_filter(demonstrated, column="addressLine2", placeholder="${q}")

    assert rewritten is not None
    assert "%22column%22%3A%22addressLine2%22" in rewritten
    assert "${q}" in rewritten
    # The site is the deployment; the offset was somebody's scroll position.
    assert "siteId=SG" in rewritten
    assert "offset" not in rewritten


def test_an_endpoint_that_showed_no_filter_is_left_alone() -> None:
    """Inventing a filter for an API that never showed us one is a guess."""
    assert as_a_filter(LIST, column="x", placeholder="${q}") is None


def _dropdown() -> Options:
    """A real listing that answered 200 with a filter on it."""
    return Options(
        label=("addressName",),
        value="id",
        url=(
            "https://wms.test/wm/addresses?query="
            + json.dumps(
                [{"column": "addressName", "operator": "EQ", "value": "*h*"}],
                separators=(",", ":"),
            )
            + "&limit=10&siteId=SG"
        ),
        search="addressName",
    )


def _asked_for(typed: str) -> str:
    """What the search term actually says, read back out of the URL."""
    url = str(_searched(_dropdown(), typed))
    query = dict(parse_qsl(urlsplit(url).query))["query"]
    return str(json.loads(query)[0]["value"])


@pytest.mark.parametrize(
    "typed",
    [
        "ACME",
        # The one that was broken. A quote is ordinary in an address line --
        # `ATTN "ALI"` -- and it searched for the backslash in front of it, so
        # the field that most needed a search silently found nothing.
        'ATTN "ALI"',
        "C:\\dock",
        # Not a query parameter of its own, whatever it looks like.
        "A&limit=9999",
    ],
)
def test_a_dropdown_searches_for_exactly_what_was_typed(typed: str) -> None:
    """`as_a_filter` builds the term with `json.dumps` and the query with
    `urlencode`, so the JSON it sits inside and the URL it rides on are both
    already its business. Escaping first was the double-encoding this file's
    own neighbours warn about, in the other dimension."""
    assert _asked_for(typed) == typed


def test_a_typed_value_cannot_add_a_second_search_term() -> None:
    url = str(_searched(_dropdown(), '*", "column": "password"'))
    terms = json.loads(dict(parse_qsl(urlsplit(url).query))["query"])

    assert len(terms) == 1
    assert terms[0]["column"] == "addressName"
