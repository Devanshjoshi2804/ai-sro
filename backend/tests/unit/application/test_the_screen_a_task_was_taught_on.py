"""Which screen a skill has to be on before it can be performed.

A task taught by clicking names no URL on any step. Until the version recorded
where the demonstration began, a run could only be performed by an operator who
had already navigated to the right screen themselves -- and one who had not read
thirteen `control_not_found` lines that said nothing whatever about being on the
wrong page. The recorder had been sending the page with every gesture the whole
time; only the accessibility snapshot ever kept it, so a demonstration made of
pure gestures recorded nothing about where it happened.
"""

from __future__ import annotations

from sro.application.induction.induce_skill import _started_on
from sro.domain.recording.recording import Recording
from tests import factories


def _demonstration(*pages: str | None) -> Recording:
    """A recording whose frames happened on those pages, in that order."""
    taught = factories.recording(frames=0)
    for index, page in enumerate(pages):
        taught.append_frame(factories.frame(index, page_url=page))
    return taught


WORK_AREAS = "https://wms.example/portal?siteId=SG#wm.config/wm.config.work.work.areas"
WAREHOUSE = "https://wms.example/portal?siteId=SG#wm.config/wm.config.warehouse"


def test_the_screen_is_the_one_the_demonstration_opened_on() -> None:
    """The first frame, not the last. The first is the screen the operator was
    looking at when they began, which is what a run has to reproduce; the last
    is wherever the task happened to leave them."""
    taught = _demonstration(WORK_AREAS, WORK_AREAS, WAREHOUSE)

    assert _started_on(taught) == WORK_AREAS


def test_two_demonstrations_that_began_elsewhere_name_no_screen() -> None:
    """A disagreement is evidence, not a tie to break.

    Both operators did the task; they started from different places. That says
    the screen is not part of the task, and a run that navigated on it would
    send itself somewhere only one of the two had ever been.
    """
    assert _started_on(_demonstration(WORK_AREAS), _demonstration(WAREHOUSE)) is None


def test_one_demonstration_that_recorded_nothing_is_an_absence_not_a_veto() -> None:
    """Everything taught before the recorder kept the page has `None` on every
    frame. Treating that as disagreement would mean a skill re-taught once could
    never learn its screen until every older demonstration was thrown away."""
    assert _started_on(_demonstration(WORK_AREAS), _demonstration(None)) == WORK_AREAS


def test_nothing_recorded_anywhere_is_no_screen() -> None:
    assert _started_on(_demonstration(None, None)) is None
    assert _started_on(None) is None
    assert _started_on() is None


def test_the_tab_is_read_off_the_gesture_and_the_frame_is_not() -> None:
    """The tab's URL, not the frame's.

    A gesture inside a portal that hosts its screens in an iframe reports the
    frame's own src -- `/portal/page?libraryContext=...`, a document that means
    nothing outside the shell that gives it its session. A run told to open that
    would load half an application. What has to be reproduced is the address an
    operator would type, which only the worker knows, and which it now sends
    beside the frame's.
    """
    from datetime import UTC, datetime

    from sro.application.observation.teach import _capture
    from sro.domain.observation.candidate import Episode
    from sro.domain.shared.identifiers import BatchId

    during = Episode(
        started_at=datetime(2026, 8, 31, 7, 0, tzinfo=UTC),
        ended_at=datetime(2026, 8, 31, 7, 30, tzinfo=UTC),
        host="wms.example",
        batch_ids=(BatchId("bat-1"),),
    )
    read = _capture(
        {
            "kind": "gesture",
            "gesture": {
                "kind": "click",
                "at": "2026-08-31T07:10:00Z",
                "target": {"cssPath": "span#addButton"},
                "url": "https://wms.example/portal/page?libraryContext=f4d6755a",
            },
            "frame_url": "https://wms.example/portal/page?libraryContext=f4d6755a",
            "page_url": WORK_AREAS,
        },
        during,
    )

    assert read is not None
    assert read.page_url == WORK_AREAS


def test_a_gesture_from_a_browser_that_sends_no_page_records_none() -> None:
    """Every extension in the field before this sent no `page_url`, and its
    uploads still have to assemble. An absence is an absence, not a crash
    halfway through a demonstration."""
    from datetime import UTC, datetime

    from sro.application.observation.teach import _capture
    from sro.domain.observation.candidate import Episode
    from sro.domain.shared.identifiers import BatchId

    during = Episode(
        started_at=datetime(2026, 8, 31, 7, 0, tzinfo=UTC),
        ended_at=datetime(2026, 8, 31, 7, 30, tzinfo=UTC),
        host="wms.example",
        batch_ids=(BatchId("bat-1"),),
    )
    read = _capture(
        {
            "kind": "gesture",
            "gesture": {
                "kind": "click",
                "at": "2026-08-31T07:10:00Z",
                "target": {"cssPath": "span#addButton"},
                "url": "https://wms.example/portal",
            },
        },
        during,
    )

    assert read is not None
    assert read.page_url is None
