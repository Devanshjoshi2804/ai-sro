"""The reading that decides whether a sentence answers the standing question.

What these pin is the falling back. A reading is a model call on the path
between a person pressing Enter and anything happening, and every way it can
fail has to end with the panel behaving as it did before the reading existed --
because a panel that quietly stops accepting answers when a model is
unreachable is worse than one that takes too many.
"""

from __future__ import annotations

from typing import Any

from sro.application.chat.reading_an_answer import IsItAnAnswer
from sro.application.context import RequestContext
from sro.domain.chat.asking import Pending
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.shared.prices import Answer
from tests import factories as f

CTX = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("devansh"))

ASKING = Pending(
    workflow_id="wfl_1",
    title="Create a Customer Type",
    values={},
    missing=("Customer Type",),
    limits={"Customer Type": 4},
)


class _Says:
    def __init__(self, data: object, raises: bool = False) -> None:
        self._data = data
        self._raises = raises
        self.asked = 0

    async def ask(self, **_: Any) -> Answer:
        self.asked += 1
        if self._raises:
            raise RuntimeError("the model is down")
        return Answer(data=self._data)


async def test_a_plain_value_is_never_sent_to_a_model() -> None:
    """`S057` is a value and looks like one. A reading spent proving that is a
    reading spent on nothing, on the path somebody is waiting on."""
    says = _Says({"answers": False, "value": "", "why": "should never be asked"})

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "S057")

    assert read.answers is True
    assert read.value == "S057"
    assert says.asked == 0


async def test_a_sentence_is_read_and_may_come_back_not_an_answer() -> None:
    says = _Says({"answers": False, "value": "", "why": "asking about the mail"})

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "has reply arrived")

    assert read.answers is False
    assert read.value == ""
    assert says.asked == 1


async def test_the_value_inside_a_sentence_is_what_is_taken() -> None:
    """A form typed with `the code is S057` is a wrong record with a reason."""
    says = _Says({"answers": True, "value": "S057", "why": "names the code"})

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "the code is S057")

    assert read.value == "S057"


async def test_a_reading_that_raises_says_it_could_not_tell() -> None:
    """An unreadable answer is not an answer. Taking the raw text as the value
    is how `HAS REPLY ARRIVED` reached a four-character box; the safe fallback
    is a third state the caller re-asks under, not a value nobody gave."""
    says = _Says(None, raises=True)

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "has reply arrived")

    assert read.answers is None
    assert read.value == ""


async def test_a_deployment_with_no_model_says_it_could_not_tell() -> None:
    read = await IsItAnAnswer(None, model="m").execute(CTX, ASKING, "has reply arrived")

    assert read.answers is None
    assert read.value == ""


async def test_a_reply_with_no_data_says_it_could_not_tell() -> None:
    says = _Says(None)

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "has reply arrived")

    assert read.answers is None
    assert read.value == ""


async def test_an_answer_with_no_value_in_it_falls_back_to_the_sentence() -> None:
    """A reading that says "this answers" and hands back nothing has not read
    anything, and what was said is the best thing left."""
    says = _Says({"answers": True, "value": "", "why": ""})

    read = await IsItAnAnswer(says, model="m").execute(CTX, ASKING, "call it GU9")

    assert read.value == "call it GU9"
