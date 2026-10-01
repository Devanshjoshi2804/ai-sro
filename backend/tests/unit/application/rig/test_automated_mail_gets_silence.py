"""RFC 3834: a machine's mail (an auto-reply, a bounce, a list or bulk mail, an
alert) is never answered and never read for work, whatever its body says."""

import json

import pytest

from tests.unit.application.rig.test_from_the_mail import CTX, mail_world

_BODY = "Location: A1\nAction: add customer type GT2"


def _mail(sender: str, headers: dict[str, str]) -> str:
    return json.dumps(
        {
            "id": "m-1",
            "subject": "Alert",
            "body": _BODY,
            "thread_id": "",
            "from": sender,
            "headers": headers,
        }
    )


_PERSON = "Tanisha <tanisha@example.com>"


@pytest.mark.parametrize(
    ("sender", "headers"),
    [
        (_PERSON, {"auto-submitted": "auto-replied"}),
        (_PERSON, {"auto-submitted": "auto-generated"}),
        (_PERSON, {"x-auto-response-suppress": "All"}),
        (_PERSON, {"precedence": "bulk"}),
        (_PERSON, {"precedence": "Junk"}),
        (_PERSON, {"precedence": "list"}),
        (_PERSON, {"list-unsubscribe": "<mailto:u@example.com>"}),
        (_PERSON, {"x-autoreply": "yes"}),
        (_PERSON, {"x-autorespond": "yes"}),
        (_PERSON, {"content-type": 'multipart/report; report-type=delivery-status; boundary="x"'}),
        ("Mail Delivery Subsystem <mailer-daemon@googlemail.com>", {}),
        ("postmaster@example.com", {}),
    ],
)
async def test_a_machine_s_mail_is_neither_answered_nor_read_for_work(
    sender: str, headers: dict[str, str]
) -> None:
    world = await mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)
    world.mailbox._answers["m-1"] = _mail(sender, headers)

    looked = await world.from_the_mail.execute(CTX)

    assert looked.offered == () and not world.reads.saw and world.durable.runs_started == []


@pytest.mark.parametrize(
    "headers",
    [{}, {"auto-submitted": "no"}, {"precedence": "first-class"}, {"content-type": "text/plain"}],
)
async def test_a_person_s_mail_is_still_read(headers: dict[str, str]) -> None:
    world = await mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)
    world.mailbox._answers["m-1"] = _mail(_PERSON, headers)

    looked = await world.from_the_mail.execute(CTX)

    assert looked.offered and world.reads.saw
