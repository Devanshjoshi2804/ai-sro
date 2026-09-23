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
from sro.application.induction.understand import UnderstandRecording
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import RecordingId
from tests import factories as f
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
