"""Provenance says which demonstrations shaped the steps, not only how many
recordings a version cites.

Before this, a skill induced from four occurrences recorded four recording
ids -- full stop. That was true and it was also the whole defect: only the
pair ever reached `align_all`, so two of the four shaped no step at all, and
`recording_ids` alone could not tell a reader which two. Somebody checking why
a skill declared a parameter no step could fill would find four demonstrations
listed and nothing saying two of them only ever touched the parameters.

`Provenance.aligned_recording_ids` is the answer: the subset of
`recording_ids` that actually reached `align_all`, so a reader can tell
"aligned for steps" apart from "read for parameters only" without recomputing
anything the induction already knew.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.induction.companions import read_skills
from sro.application.induction.understand import UnderstandRecording
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId, SkillId
from tests import factories as f
from tests.unit.application.test_a_task_done_many_ways import (
    _every_short_line,
    _four_carrier_cross_references,
    _induce,
)
from tests.unit.application.test_capabilities import _read
from tests.unit.application.test_understand import FakeInterpreter, _recorded
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def test_a_recording_cannot_be_aligned_without_being_cited_at_all() -> None:
    """The subset relationship is an invariant, not a convention two call
    sites happen to honour today."""
    with pytest.raises(InvariantViolation, match="subset"):
        f.provenance(
            recording_ids=(RecordingId("rec-1"), RecordingId("rec-2")),
            aligned_recording_ids=(RecordingId("rec-1"), RecordingId("rec-3")),
        )


def test_a_row_written_before_this_field_existed_claims_nothing() -> None:
    """`f.provenance` does not set the new field, the way a row loaded from a
    database written before this task would not either. Empty must not read
    as "recorded and none of them aligned" -- that is exactly the false
    completeness this field exists to stop -- so a reader is told nothing was
    ever recorded here, not that the answer is zero."""
    provenance = f.provenance()

    assert provenance.aligned_recording_ids == ()
    assert provenance.recording_ids != (), "the old field still says something was demonstrated"


async def test_four_demonstrations_that_do_not_loop_are_all_marked_aligned() -> None:
    """The real case from the previous task, with the missing half restored:
    not looping, so `align_all` reads every doing's steps, and the record now
    says so instead of leaving a reader to assume it from the count alone."""
    version = await _four_carrier_cross_references()
    provenance = version.provenance

    assert len(provenance.recording_ids) == 4
    assert provenance.aligned_recording_ids == provenance.recording_ids


async def test_a_loops_history_is_marked_read_for_parameters_only() -> None:
    """The subtlety a reader cannot be left to guess: where the pair loops,
    `loops.detect` excludes the rest of the history from `align_all` on
    purpose, so those recordings proved parameters and nothing about the
    steps. `recording_ids` still cites all four -- they were still read -- but
    `aligned_recording_ids` must be the pair alone, or the record would claim
    a looping skill's history shaped steps it never touched."""
    version = await _induce(
        _every_short_line("1", "2"),
        _every_short_line("1", "2", "3"),
        _every_short_line("1", "2"),
        _every_short_line("1", "2"),
    )
    provenance = version.provenance

    assert len(provenance.recording_ids) == 4
    assert provenance.aligned_recording_ids == provenance.recording_ids[:2]
    assert set(provenance.recording_ids[2:]).isdisjoint(provenance.aligned_recording_ids), (
        "history read only for parameters must not also be claimed as aligned"
    )


# --- The other two constructors -----------------------------------------------
#
# `InduceSkill` is not the only place a `Provenance` gets built. `companions.py`
# and `understand.py` each build a version from exactly one recording, and each
# had its own `Provenance(...)` call site that predates this field -- which
# means the field's default, `()`, is what a fresh skill from either path would
# say today unless each is told explicitly. That is precisely the ambiguity
# the field exists to end, reintroduced by omission rather than by mistake: a
# version written tomorrow reading identically to a version written before the
# field existed.


async def test_a_companion_read_skill_marks_its_one_recording_as_aligned() -> None:
    """`companions._skill` builds its one read step from exactly the recording
    it read the collection on. A single-recording constructor, the same shape
    `understand.py` and `InduceSkill`'s one-run branch are -- and it must say
    so the same way, not fall through to the "nobody recorded this" default."""
    frames = (_read(0, "warehouseTransportModes", rows=3),)
    taught = f.objective(objective_type="create_transport_mode", entity_type="transport_mode")

    companions = read_skills(
        frames,
        taught=taught,
        recording_id=RecordingId("rec-1"),
        tenant_id=f.TENANT,
        by=f.OPERATOR,
        at=f.at(0),
        new_id=lambda: SkillId("companion-1"),
    )

    assert len(companions) == 1
    provenance = companions[0].versions[-1].provenance
    assert provenance.recording_ids == (RecordingId("rec-1"),)
    assert provenance.aligned_recording_ids == (RecordingId("rec-1"),)


async def test_understanding_one_recording_marks_it_as_aligned() -> None:
    """`UnderstandRecording` reads every step from the one recording it was
    given -- there is no pair, no history, nothing else the steps could have
    come from. Its `Provenance(...)` call site must say that plainly rather
    than leave the default to imply nobody wrote it down."""
    uow = FakeUnitOfWork()
    await _recorded(uow)

    await UnderstandRecording(uow, FakeInterpreter(), FakeClock(), FakeIdFactory()).execute(
        CTX, recording_id=RecordingId("rec-1")
    )

    version = next(iter(uow.skills.rows.values())).versions[-1]
    assert version.provenance.recording_ids == (RecordingId("rec-1"),)
    assert version.provenance.aligned_recording_ids == (RecordingId("rec-1"),)
