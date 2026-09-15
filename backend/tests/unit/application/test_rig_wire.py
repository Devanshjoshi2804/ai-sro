"""The rig's protocol arrives whole: a batch parses, one bad event does not
cost the batch, and the correlator hands the domain what the arithmetic reads."""

from typing import cast

from sro.application.capture.rig_wire import parse_batch
from sro.application.observation.correlate import correlate, system_of
from sro.domain.shared.hosts import page_of
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


def test_a_url_that_names_no_system_names_no_page_either() -> None:
    assert page_of(None) is None
    assert page_of("") is None
    assert page_of("about:blank") is None
    assert page_of("/portal/page") is None
