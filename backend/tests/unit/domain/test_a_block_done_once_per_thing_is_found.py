"""Finding the repeated block in what an operator was seen doing.

An operator added three warehouse equipment types in a row. `one_occurrence`
strikes every citation but one doing's, so the job that comes out describes one
pass -- and the other two are sitting in the evidence past its last citation,
proving the block is a block.

What is counted is the CREATE and not the clicks. Real evidence never repeats a
gesture sequence exactly: somebody scrolls, checks a row, clicks the grid
between one record and the next. Matched on sequences, this found nothing at
all on a real tenant's day; matched on the endpoint the create goes to, it
found the two jobs that really do repeat and left the six that do not.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Call, Gesture, Target
from sro.domain.skill.repeats import K_SETTLE_S, detect
from sro.domain.skill.workflow import Step, Workflow

WMS = "https://wms.test"
MAIL = "https://mail.test"
CREATE = f"{WMS}/data/WM/wm/equipmentTypes"


def _gesture(
    gesture_id: str,
    at: float,
    *,
    kind: str = "click",
    url: str = WMS,
    status: int | None = None,
    body: str | None = None,
    method: str = "POST",
) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="new",
        stream_id="str-1",
        batch_id="bat-1",
        at=at,
        url=url,
        system=url,
        tab_id=7,
        frame_url=None,
        action=Action(kind=kind, at=at, url=url, target=Target(tag="button", name="Save")),
        requests=()
        if status is None
        else (Call(method=method, url=CREATE, status=status, started_at=at, request_body=body),),
    )


def _added(codes: tuple[str, ...], *, status: int = 201, at: float = 100.0) -> dict[str, Gesture]:
    """One sitting: a mail read once, then a record made per code."""
    made: dict[str, Gesture] = {"ges-mail": _gesture("ges-mail", at - 10, url=MAIL)}
    for index, code in enumerate(codes):
        moment = at + index * 30
        made[f"ges-add-{index}"] = _gesture(f"ges-add-{index}", moment)
        made[f"ges-type-{index}"] = _gesture(f"ges-type-{index}", moment + 5, kind="type")
        made[f"ges-save-{index}"] = _gesture(
            f"ges-save-{index}", moment + 10, status=status, body=f'{{"code":"{code}"}}'
        )
    return made


def _job() -> Workflow:
    """As the model wrote it: the mail once, then one pass of the making."""
    return Workflow(
        id="wfl_1",
        tenant="new",
        title="Create a Warehouse Equipment Type",
        narrative="n",
        systems=[WMS, MAIL],
        steps=[
            Step(order=0, says="Read the mail.", system=MAIL, cites=["ges-mail"]),
            Step(order=1, says="Click Add.", system=WMS, cites=["ges-add-0"]),
            Step(order=2, says="Type the code.", system=WMS, cites=["ges-type-0"]),
            Step(order=3, says="Click Save.", system=WMS, cites=["ges-save-0"]),
        ],
    )


def test_a_block_the_operator_did_three_times_is_found() -> None:
    found = detect(_job(), _added(("8SITDOWN", "8STANDUP", "8REACHT")))

    assert found is not None
    assert (found.first_step, found.last_step) == (1, 3)


def test_the_step_that_read_the_mail_is_not_in_the_block() -> None:
    """The mail was read once and says what all three records are. A job that
    repeated the reading would open the message three times and make one
    record."""
    found = detect(_job(), _added(("A", "B")))

    assert found is not None and not found.covers(0)


def test_a_job_done_once_repeats_nothing() -> None:
    assert detect(_job(), _added(("ONLY",))) is None


def test_two_identical_creates_are_one_record_posted_twice() -> None:
    """A double submit, a retry, a page that resent on a slow network. Learning
    that as a list of two is learning a mistake."""
    twice = _added(("SAME", "SAME"))

    assert detect(_job(), twice) is None


def test_a_page_that_talks_is_not_a_job_being_repeated() -> None:
    """Gmail's own `POST /mail/u/*/` came back 200 fourteen times in one real
    doing. A detector counting mutations would have called drafting one message
    a job done fourteen times."""
    assert detect(_job(), _added(("A", "B"), status=200)) is None


def test_the_same_task_after_lunch_is_not_a_repeated_block() -> None:
    """Twice today is a task done twice. The block repeating is about one
    sitting, and a pause is where a sitting ends."""
    morning = _added(("A",))
    afternoon = _added(("B",), at=100.0 + K_SETTLE_S + 60)
    both = {**morning, **{f"pm-{key}": value for key, value in afternoon.items()}}

    assert detect(_job(), both) is None


def test_a_job_whose_evidence_is_gone_says_nothing() -> None:
    assert detect(_job(), {}) is None
