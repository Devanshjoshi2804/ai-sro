"""The rig's protocol arrives whole: a batch parses, one bad event does not
cost the batch, and the correlator hands the domain what the arithmetic reads."""

from typing import cast

from sro.application.capture.rig_wire import parse_batch
from sro.application.observation.correlate import correlate, system_of
from sro.domain.shared.hosts import page_of, screen_of
from tests.unit.domain.rig.conftest import BATCH

# BATCH is typed `dict[str, object]` so its bytes can hold any event shape a
# test wants to throw at it; `events` is always the list it looks like.
_events = cast("list[object]", BATCH["events"])


def test_the_measured_batch_parses_and_correlates() -> None:
    batch, rejected = parse_batch(BATCH)
    assert rejected == ()
    gestures, _requests, _pages, _dropped = correlate(batch, "acme")
    assert len(gestures) == 7
    assert {g.action.kind for g in gestures} == {"type", "select", "upload", "click", "press"}
    typed = next(g for g in gestures if g.action.value == "ACME-4471")
    assert typed.action.target and typed.action.target.name == "Client Code"
    assert typed.system == "http://127.0.0.1:63319"


def test_one_unparseable_event_does_not_cost_the_batch() -> None:
    raw = dict(BATCH, events=[*_events, {"kind": "gesture", "gesture": {"kind": "wave"}}])
    batch, rejected = parse_batch(raw)
    assert len(rejected) == 1 and rejected[0].index == len(_events)
    assert len(batch.events) == len(_events)


def test_system_of_is_the_origin() -> None:
    assert system_of("https://wms.example:8443/a/b?c=1") == "https://wms.example:8443"
    assert system_of(None) is None
    assert system_of("about:blank") is None


def test_the_page_a_url_names_is_not_the_visit_it_records() -> None:
    """Query and fragment both go, and both for one reason: they are where a
    system puts what is particular to one visit. Real captured urls, 2026-09-15
    -- a message id in one, a session token in the other."""
    assert (
        page_of("https://mail.google.com/mail/u/0/?tab=rm&ogbl#inbox/FMfcgzQhWLSTRpPPfBFF")
        == "https://mail.google.com/mail/u/0/"
    )
    assert (
        page_of("https://wms.example/portal/page?libraryContext=f4d6755ab6b6&siteId=SG#wm.config")
        == "https://wms.example/portal/page"
    )


def test_the_page_keeps_its_scheme_because_what_reads_it_parses_it() -> None:
    """The extension reduces this further to host-and-path the moment it lands
    (`nudge.page`), and that reduction runs `new URL()`. Handed a bare
    `host/path` it throws, catches, and returns the empty string -- which is
    every arrival offer silently gone, with nothing to say why."""
    page = page_of("https://mail.google.com/mail/u/0/?tab=rm#inbox/FMfcg")

    assert page is not None and page.startswith("https://")


# -- what two doings of one step agree on --------------------------------------
#
# `page_of` drops the query and the fragment because, given ONE url, nothing
# says which parts of them name a screen and which name that visit to it. Given
# two, the demonstrations say: what moved is the particular. Every case below is
# a real url off the deployment, 2026-09-15.


MAIL = "https://mail.google.com/mail/u/0/?tab=rm&ogbl#inbox/FMfcgzQhWLSTRpPPfBFF"


def test_one_doing_agrees_with_itself_and_comes_back_whole() -> None:
    """The honest answer, not a fallback. With a single demonstration nothing
    has said which half of the url was the job."""
    assert screen_of([MAIL]) == MAIL
    assert screen_of([MAIL, MAIL]) == MAIL, "and two doings of the same visit say no more"


def test_two_mails_agree_on_the_inbox_and_not_on_the_message() -> None:
    other = "https://mail.google.com/mail/u/0/?tab=rm&ogbl#inbox/ZZZZZZZZZZZZ"

    assert screen_of([MAIL, other]) == "https://mail.google.com/mail/u/0/?tab=rm&ogbl"


def test_a_warehouse_keeps_the_fragment_its_screens_are_addressed_by() -> None:
    """The case that makes a rule about fragments wrong. Two doings of a step
    performed on the same screen agree on it, and it survives -- where
    `page_of` would have dropped it and sent a run to the portal root."""
    screen = "https://wms.example/portal?siteId=SG#wm.config/wm.config.partners.customers.types"

    assert screen_of([screen, screen]) == screen


def test_two_doings_reached_from_different_screens_keep_neither() -> None:
    """The bug this found, on the deployment's own row. Step 2 of `Create a
    Customer Type` is "Navigate to the Customer Types screen", and its two
    cited gestures sit on the screens the operator happened to be on when they
    reached for the menu -- neither of them this step's. A run resuming there
    opened whichever one `primary_gesture` picked."""
    was_on = "https://wms.example/portal?siteId=SG#wm.config/wm.config.inbound.receiving.optimal"
    also_on = "https://wms.example/portal?siteId=SG#wm.config/wm.config.warehouse.warehouse"

    assert screen_of([was_on, also_on]) == "https://wms.example/portal?siteId=SG"


def test_a_query_is_agreed_per_parameter_because_one_carries_both_kinds() -> None:
    """`libraryContext` is a session token; `siteId` and `menu` are the screen,
    in the same query string. Whole-or-nothing would lose the menu to keep out
    the token, or keep the token to hold the menu."""
    one = "https://wms.example/portal/page?libraryContext=f4d6755ab6b6&siteId=SG&menu=wm.config"
    two = "https://wms.example/portal/page?libraryContext=99999999aaaa&siteId=SG&menu=wm.config"

    assert screen_of([one, two]) == "https://wms.example/portal/page?siteId=SG&menu=wm.config"


def test_a_value_comes_back_spelled_the_way_the_browser_spelled_it() -> None:
    """Raw segments, not parsed pairs. Re-encoding a query is how a url that
    worked stops working."""
    kept = "https://wms.example/p?redirect_uri=https%3a%2f%2fa.example%2fx&q=a+b"

    assert screen_of([kept, kept]) == kept


def test_a_visit_to_another_host_is_not_another_doing_of_this_screen() -> None:
    """Ignored rather than allowed to erase everything. A step can cite a
    gesture from the other side of a cross-system job, and the anchor decides
    whose screen is being named."""
    assert screen_of([MAIL, "https://wms.example/portal?siteId=SG"]) == MAIL


def test_nothing_to_agree_on_names_no_screen() -> None:
    assert screen_of([]) is None
    assert screen_of([None, None]) is None
    assert screen_of(["about:blank"]) is None
    assert screen_of(["/portal/page", MAIL]) is None, "the anchor names no system"


def test_a_url_that_names_no_system_names_no_page_either() -> None:
    assert page_of(None) is None
    assert page_of("") is None
    assert page_of("about:blank") is None
    assert page_of("/portal/page") is None
