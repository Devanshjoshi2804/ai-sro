"""What a job's boxes hold, before any run has typed into one.

`workflow_learned.holds` is the measurement, and it costs a wrong record to
make. The knowledge base has held the declarations all along -- 404 payload
keys with their labels and their `maxLength`, and 88 real create forms -- and
nothing ever asked them about a JOB's parameters.

What these pin is the join and the arithmetic around it: the label is the only
bridge from a parameter's name to a body key, the lowest ceiling binds whatever
named it, and a label two keys answer to decides nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.execution.declared import declared_limits, screen_for
from sro.domain.execution.learned_step import LearnedStep, limits_for
from sro.domain.knowledge.entry import (
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.workflow import Step, Workflow
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

SCREEN = "https://wms.example.com/#wm.config/wm.config.partners.customers.types////"


def _claim(
    kind: EntryKind, key: str, body: dict[str, object], evidence: EvidenceLevel
) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeId(f"kb-{kind}-{key}"),
        tenant_id=f.TENANT,
        system="blue_yonder",
        kind=kind,
        key=key,
        title=key,
        body=body,
        source="index/field-dictionary.json",
        evidence=evidence,
        observed_at=datetime.now(tz=UTC),
    )


async def _knows(uow: FakeUnitOfWork, *claims: KnowledgeEntry) -> FakeUnitOfWork:
    for claim in claims:
        await uow.knowledge.add(claim)
    return uow


def _field(key: str, labels: list[str], max_length: int | None) -> KnowledgeEntry:
    return _claim(
        EntryKind.FIELD,
        key,
        {"labels": labels, "max_length": max_length},
        EvidenceLevel.ASSERTED,
    )


def _form(route: str, fields: list[dict[str, object]]) -> KnowledgeEntry:
    return _claim(EntryKind.FORM, route, {"fields": fields}, EvidenceLevel.OBSERVED)


async def test_a_job_knows_what_its_boxes_hold_before_a_run_has_typed_into_one() -> None:
    """The point of the whole exercise.

    `Customer Type Description` is posted as `longDescription`, and nothing in
    the job says so -- a mined parameter is a label off a screen. The vendor's
    dictionary is what joins them, and it has been in the store since before
    the rig could type.
    """
    uow = await _knows(
        FakeUnitOfWork(),
        _field("longDescription", ["Customer Type Description", "Description"], 2000),
        _field("customerType", ["Customer Type"], 60),
    )

    limits = await declared_limits(uow, f.TENANT, ["Customer Type", "Customer Type Description"])

    assert limits == {"Customer Type": 60, "Customer Type Description": 2000}


async def test_the_form_an_operator_actually_uses_beats_the_manual() -> None:
    """Measured on QA 2026-09-16: the dictionary says `customerType` holds 60,
    the Customer Types create form says 4, and the ledger's own gotcha --
    somebody sitting in front of the screen -- says `csttyp truncates at 4
    chars`. Two of the three agree, and reading the third sends `NEWSROTEST`,
    keeps `NEWS`, and answers 201."""
    uow = await _knows(
        FakeUnitOfWork(),
        _field("customerType", ["Customer Type"], 60),
        _form(
            "#wm.config/wm.config.partners.customers.types////",
            [{"field": "customerType", "label": "Customer Type", "maxLength": 4}],
        ),
    )

    limits = await declared_limits(uow, f.TENANT, ["Customer Type"], SCREEN)

    assert limits == {"Customer Type": 4}


async def test_another_screen_s_form_lends_this_one_nothing() -> None:
    """A body key does not name a form: `customerType` is posted by two of them
    on this deployment, so a join by key alone would hand one screen's numbers
    to another screen's write."""
    uow = await _knows(
        FakeUnitOfWork(),
        _field("customerType", ["Customer Type"], 60),
        _form(
            "#wm.config/wm.config.partners.customers.existing////",
            [{"field": "customerType", "label": "Customer Type", "maxLength": 4}],
        ),
    )

    limits = await declared_limits(uow, f.TENANT, ["Customer Type"], SCREEN)

    assert limits == {"Customer Type": 60}


async def test_a_label_two_keys_answer_to_declares_nothing() -> None:
    """`Description` is a label on ten different keys on this deployment,
    holding anywhere from 20 characters to 2000. A guess between them is a
    number this would state to a person as a fact, and stopping a correct run
    on it is the one failure mode worse than the silence it replaces."""
    uow = await _knows(
        FakeUnitOfWork(),
        _field("description", ["Description"], 100),
        _field("deviceName", ["Device Name", "Description"], 20),
    )

    assert await declared_limits(uow, f.TENANT, ["Description"]) == {}
    # And the other names on the same claims are unharmed by it.
    assert await declared_limits(uow, f.TENANT, ["Device Name"]) == {"Device Name": 20}


async def test_a_field_nothing_documents_declares_nothing_rather_than_a_guess() -> None:
    """Which changes nothing for such a job: the first run finds the limit out
    the hard way exactly as it did before. `Warehouse.Description` is the real
    case -- it truncates at about 28 characters and the dictionary has never
    heard of the screen."""
    uow = await _knows(FakeUnitOfWork(), _field("customerType", ["Customer Type"], 60))

    assert await declared_limits(uow, f.TENANT, ["Warehouse Description"]) == {}
    assert await declared_limits(uow, f.TENANT, []) == {}


async def test_a_claim_with_no_number_on_it_is_not_a_limit_of_zero() -> None:
    uow = await _knows(FakeUnitOfWork(), _field("customerType", ["Customer Type"], None))

    assert await declared_limits(uow, f.TENANT, ["Customer Type"]) == {}


async def test_a_name_the_screen_punctuates_differently_still_joins() -> None:
    """A mined parameter is a label lifted off a screen, and screens put colons
    and capitals where a job's parameter list does not."""
    uow = await _knows(FakeUnitOfWork(), _field("customerType", ["Customer Type:"], 60))

    assert await declared_limits(uow, f.TENANT, ["customer type"]) == {"customer type": 60}


async def test_what_a_run_measured_and_what_the_manual_claims_are_both_ceilings() -> None:
    """Neither overrules the other. A limit is a ceiling, so every ceiling
    applies and the lowest one binds -- being wrong low asks somebody to
    shorten a value further than they had to, and being wrong high writes a
    record that does not say what was asked for."""
    steps = [Step(order=0, says="type it", system=None, cites=["g"], parameters=["Description"])]
    learnt = (LearnedStep(0, "component", "textfield-1", "sight", holds=28),)

    # The manual is looser than the box turned out to be.
    assert limits_for(steps, learnt, {"Description": 2000}) == {"Description": 28}
    # And tighter, on a field no run has hit yet.
    assert limits_for(steps, (), {"Description": 100}) == {"Description": 100}
    # A declared name this job does not type is still this job's to answer for:
    # `unasked` names them, and a limit is worth saying about those too.
    assert limits_for(steps, learnt, {"Code": 4}) == {"Description": 28, "Code": 4}


async def test_the_screen_a_job_is_on_is_what_its_own_demonstrations_agree_on() -> None:
    """A job with no citations has no screen, and gets the dictionary alone --
    which is the weaker half. Worth one read of the gestures to avoid."""
    uow = FakeUnitOfWork()
    bare = Workflow(
        id="wfl_1",
        tenant=f.TENANT.value,
        title="Create a Customer Type",
        narrative="open, type, save",
        steps=[Step(order=0, says="type it", system=None, cites=[])],
    )

    assert await screen_for(uow, f.TENANT, bare) == ""


def _gesture(gesture_id: str, url: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=f.TENANT.value,
        stream_id="str-1",
        batch_id="bat-1",
        at=1_739_314_800.0,
        url=url,
        page_url=url,
        system="wms",
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=1_739_314_800.0, url=url),
    )


async def test_the_screen_is_where_the_typing_happens_not_where_the_job_opens() -> None:
    """Measured on QA 2026-09-18, against the real `Create a Customer Type`.

    Its six steps open a MAIL, navigate to the WMS, press Add, type twice and
    Save. Given all six steps' citations, `screen_of` anchors on the first url
    it is handed and answers with the Gmail inbox -- so the form half matched
    nothing, `Customer Type` came back as the manual's 60 rather than the real
    form's 4, and a card would have accepted `NEWSROTEST`, sent it, kept `NEWS`
    and been answered 201.

    A limit is a fact about the box a value is typed into.
    """
    uow = FakeUnitOfWork()
    mail = "https://mail.google.com/mail/u/0/#inbox/FMfcgz"
    await uow.gestures.add_gestures(
        tuple(
            _gesture(one, url)
            for one, url in (("g-mail", mail), ("g-type", SCREEN), ("g-save", SCREEN))
        )
    )
    job = Workflow(
        id="wfl_1",
        tenant=f.TENANT.value,
        title="Create a Customer Type",
        narrative="open the mail, go to the WMS, type, save",
        steps=[
            Step(order=1, says="open the email", system=None, cites=["g-mail"]),
            Step(
                order=4,
                says="type the code",
                system=None,
                cites=["g-type"],
                parameters=["Customer Type"],
            ),
            Step(order=6, says="press Save", system=None, cites=["g-save"]),
        ],
    )

    screen = await screen_for(uow, f.TENANT, job)

    assert "mail.google.com" not in screen, screen
    assert screen.startswith(SCREEN[: SCREEN.index("#")]), screen


async def test_a_job_that_types_nowhere_names_no_screen() -> None:
    """The honest reading rather than a fallback to every step: a job with no
    typing step has no form to be measured against, and widening the net to
    find one is how the Gmail url got in here."""
    uow = FakeUnitOfWork()
    await uow.gestures.add_gestures((_gesture("g-1", SCREEN),))
    job = Workflow(
        id="wfl_1",
        tenant=f.TENANT.value,
        title="Navigate to Receiving",
        narrative="open the screen",
        steps=[Step(order=0, says="click", system=None, cites=["g-1"])],
    )

    assert await screen_for(uow, f.TENANT, job) == ""
