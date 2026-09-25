"""The acceptance test is the real blob, not an invented one.

Measured on this tenant's own captured traffic, comparing what the extension
uploaded against what the backend stored:

    as the browser sent it:   974,397 chars, 0 «redacted» markers, 1 JWT, 1 &code=
    after the rig's boundary: 518 markers, 0 JWTs, 0 &code=

The client-side rules did not fire on that traffic at all, and the backend --
which calls `admit()`, then `_ndjson()`, then `blobs.put()`, and redacted at no
point in between -- kept a live JWT and the OAuth authorization code carrying
it. Both are in `s3://sro-artifacts/acme/...` today; see the report.

The fixture beside this file is that batch. Seven of its forty events, with
every credential value replaced by a stand-in of the same SHAPE -- a JWT whose
signature is the word `not-a-signature`, an opaque token where an opaque token
was -- because committing a live Blue Yonder production token to a git
repository to prove it gets redacted would be the same mistake in a longer
loop. The structure, the parameter names, the repeated query keys, the
percent-encoding and the hosts are the real ones, untouched.

Two of the seven events are reconstructed rather than copied: the extension's
own redaction HAD emptied the `authorization`, `X-CSRF-TOKEN` and
`CSRF-ENCRYPT-TOKEN` headers and nulled the password gesture's value before
uploading, and this test exists precisely because the backend cannot depend on
that. So the fixture carries what a browser running no rules would have sent.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from sro.application.context import RequestContext
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.policy import SetObservationPolicy
from sro.application.observation.redact import redact_events
from sro.application.observation.register import RegisterDevice
from sro.domain.observation.batch import CaptureMode
from sro.domain.observation.gesture import AfterState, Landmark, OutlineMessage
from sro.domain.observation.outline import K_OUTLINE_CHARS, K_OUTLINE_FIELDS, K_OUTLINE_OPTIONS
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.sensitivity import REDACTED
from sro.domain.shared.identifiers import BatchId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "observation"
    / "a_batch_that_carried_a_credential.ndjson"
)

ACME = RequestContext(tenant_id=TenantId("acme"), principal_id=f.OPERATOR)

_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*")
_BEARER = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}", re.IGNORECASE)
_LIVE_CODE = re.compile(r"[?&]code=(?!" + re.escape(REDACTED) + r")[^&\"]+")
"""A `code` parameter still carrying something. The literal `&code=` survives
redaction by design -- the parameter name is evidence and the value is the
credential -- so counting the substring alone would answer the wrong question."""


def _events() -> list[dict[str, object]]:
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line]


def _counts(events: object) -> dict[str, int]:
    text = json.dumps(events, ensure_ascii=False)
    return {
        "jwt": len(_JWT.findall(text)),
        "code": len(_LIVE_CODE.findall(text)),
        "bearer": len(_BEARER.findall(text)),
        "markers": text.count(REDACTED),
    }


def test_the_batch_that_is_in_the_blob_store_loses_its_credentials() -> None:
    before = _events()
    assert _counts(before) == {"jwt": 2, "code": 1, "bearer": 1, "markers": 0}, (
        "the fixture must still carry the credentials it is here to prove are removed"
    )

    after = redact_events(before)

    counted = _counts(after)
    assert counted["jwt"] == 0, "a JWT survived ingest"
    assert counted["code"] == 0, "an OAuth authorization code survived ingest"
    assert counted["bearer"] == 0, "a bearer token survived ingest"
    assert counted["markers"] > 0, "nothing was redacted at all, which is the bug"


def test_the_identity_fields_a_workflow_is_recognised_by_are_not_touched() -> None:
    """The other half of the rule, and the one with no alarm on it.

    `cssPath`, `testId`, `role`, `xtype`, `itemId` and `query` are what
    locators and shape keys are built from. Redacting one changes a workflow's
    identity between occurrences, so the same job stops matching itself and a
    mining run sees two rare tasks where there was one common one -- silently,
    with no credential anywhere near it.
    """
    before = _events()
    after = redact_events(before)

    for original, stored in zip(before, after, strict=True):
        was = (original.get("gesture") or {}).get("target")
        now = (stored.get("gesture") or {}).get("target")
        if not isinstance(was, dict) or not isinstance(now, dict):
            continue
        for field in ("cssPath", "xpath", "testId", "role", "tag", "bounds"):
            assert now.get(field) == was.get(field), field
        # And the free-text plane beside them is left alone when it holds no
        # credential: a label reading "Username or email" is the most useful
        # thing in the evidence for saying what the operator was doing.
        assert now.get("name") == was.get("name")

    signin, password = after[3], after[2]
    # An attribute VALUE that reads "password" is a LABEL -- it is how the page
    # says what the control is. The NAME rule runs on attribute keys only, and
    # running it on values instead is the over-redaction that would blank it.
    assert password["gesture"]["target"]["attributes"]["name"] == "password"
    assert password["gesture"]["target"]["attributes"]["type"] == "password"
    assert signin["gesture"]["target"]["name"] == "Sign In"
    # The operator's typed value survives where the control was not a secret
    # one; only the gesture the browser marked loses it.
    assert after[1]["gesture"]["value"] == "NOBODY01"
    assert password["gesture"]["value"] is None


def test_a_url_the_browser_sent_clean_is_stored_byte_for_byte() -> None:
    """The repeated `subsites`, the `%7B` and the 64-hex library hash on the
    real request URL all come back exactly as captured. A round-trip through a
    query parser would have collapsed and re-encoded every one of them."""
    before = _events()
    after = redact_events(before)

    untouched = [
        (was, now)
        for was, now in zip(before, after, strict=True)
        if isinstance(was.get("request"), dict)
        and "subsites" in str((was["request"] or {}).get("url"))
    ]
    assert untouched, "the fixture no longer carries the request this asserts on"
    for was, now in untouched:
        assert now["request"]["url"] == was["request"]["url"]


async def test_nothing_reaches_the_blob_store_without_passing_the_boundary() -> None:
    """One boundary, not several call sites.

    Asserted through `IngestObservation` rather than by calling `redact_events`
    again, because the defect was never that no redactor existed -- `redact_body`
    and `redact_shapes` were both here -- but that the one path an operator's
    browser uploads through called neither.
    """
    uow = FakeUnitOfWork()
    blobs = FakeBlobStore()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_with_a_credential_in_it"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=_events(),
    )

    assert stored.stored_at is not None
    written = (await blobs.read(stored.stored_at)).decode("utf-8")
    assert not _JWT.search(written), "a JWT was written to the evidence plane"
    assert not _BEARER.search(written), "a bearer token was written to the evidence plane"
    assert not _LIVE_CODE.search(written), "an OAuth code was written to the evidence plane"
    # And the marker is greppable in the bytes that were actually stored, not
    # escaped to `\\u00abredacted\\u00bb` the way `json.dumps` writes it by
    # default -- a hole a reviewer cannot grep for is a hole nobody can count.
    assert REDACTED in written


_A_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJvcGVyYXRvciJ9.c2lnbmF0dXJlLXNpZ25hdHVyZQ"
_TYPED_AT_SIGN_IN = "correct-horse-battery-staple"
_A_NOTE = "call the dentist at four"


def _hostile() -> list[dict[str, object]]:
    """What a client that ignores every rule could send: the free text of a
    text field and of a password field as the state they were left in, joined
    and unjoined."""
    events = _events()
    text, password, click = (copy.deepcopy(events[i]) for i in (1, 2, 3))
    text["gesture"]["ref"] = "r.1"
    password["gesture"].update(
        ref="r.2", prior_of="r.1", prior={"value": _A_JWT, "visible": True, "enabled": True}
    )
    click["gesture"].update(
        ref="r.3",
        prior_of="r.2",
        prior={"value": _TYPED_AT_SIGN_IN, "visible": True, "enabled": True},
    )
    unjoined = copy.deepcopy(click)
    unjoined["gesture"].update(
        ref="r.4", prior_of=None, prior={"value": _A_NOTE, "visible": True, "enabled": True}
    )
    unjoined["gesture"]["at"] += 1
    return [text, password, click, unjoined]


async def test_a_client_that_sends_typed_text_as_a_state_stores_none_of_it() -> None:
    uow = FakeUnitOfWork()
    blobs = FakeBlobStore()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_hostile_states"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=_hostile(),
    )

    assert stored.stored_at is not None
    written = (await blobs.read(stored.stored_at)).decode("utf-8")
    kept = repr(list(uow.gestures.rows.values()))
    assert len(uow.gestures.rows) == 4
    for said in (_A_JWT, _TYPED_AT_SIGN_IN, _A_NOTE):
        assert said not in written, f"{said!r} reached the evidence blob"
        assert said not in kept, f"{said!r} reached the gesture store"
    assert [one.action.after for one in uow.gestures.rows.values() if one.action.after] == [
        AfterState(None, True, True),
        AfterState(None, True, True),
    ]


def test_a_state_control_keeps_its_state_and_nothing_else() -> None:
    events = _events()

    def pair(target: dict[str, object], value: str) -> object:
        before, after = copy.deepcopy(events[3]), copy.deepcopy(events[3])
        before["gesture"].update(ref="r.1", target={**before["gesture"]["target"], **target})
        after["gesture"].update(ref="r.2", prior_of="r.1", prior={"value": value})
        return redact_events([before, after])[1]["gesture"]["prior"]["value"]

    assert pair({"role": "checkbox"}, "checked") == "checked"
    assert pair({"role": "switch"}, "unchecked") == "unchecked"
    assert pair({"role": "checkbox"}, "on") is None
    assert pair({"tag": "select", "role": "combobox"}, "Second choice") == "Second choice"
    assert pair({"tag": "select", "role": "combobox"}, _A_JWT) == REDACTED
    assert pair({"tag": "select", "secret": True}, "Second choice") is None
    assert pair({"tag": "input", "role": "combobox"}, "typed") is None
    assert pair({"tag": "input", "role": None}, "typed") is None


async def test_a_token_in_an_iframe_hop_does_not_survive_ingest() -> None:
    """E3 added `gesture.frame_path[].url`, the chain of iframe URLs a gesture
    was found through, and `_gesture` never ran it through `redact_url`: a
    token in an iframe URL's query string or fragment went to the blob store
    raw. Both a `?access_token=` and a `#id_token=` hop are checked, since
    `redact_url` treats the query and the fragment separately."""
    events = _events()
    click = copy.deepcopy(events[3])
    click["gesture"]["frame_path"] = [
        {"index": 0, "url": "https://top.example/shell"},
        {
            "index": 1,
            "url": (
                "https://embed.example/widget"
                "?access_token=live-secret-token"
                "#id_token=live-secret-id-token"
            ),
        },
    ]

    uow = FakeUnitOfWork()
    blobs = FakeBlobStore()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_with_a_token_in_a_frame_hop"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=[click],
    )

    assert stored.stored_at is not None
    written = (await blobs.read(stored.stored_at)).decode("utf-8")
    assert "live-secret-token" not in written, "an access_token in a frame hop reached the blob"
    assert "live-secret-id-token" not in written, "an id_token in a frame hop reached the blob"
    assert "https://embed.example/widget" in written, "the hop's host and path are still evidence"

    (correlated,) = uow.gestures.rows.values()
    hops = repr(correlated.action.frame_path)
    assert "live-secret-token" not in hops, "the correlated gesture kept the raw access_token"
    assert "live-secret-id-token" not in hops, "the correlated gesture kept the raw id_token"


_TYPED = "ACME-7731-QX"
_OTP = "483920"
_SECRET = "hunter2-correct-horse"  # noqa: S105 -- not a credential
_PATH_TOKEN = "9f8e7d6c5b4a39281706f5e4d3c2b1a0"  # noqa: S105 -- not a credential
_FORGED = {"headings": ["Forged Under Another Key"], "buttons": [f"Code {_OTP}"]}


def _hostile_outline() -> list[dict[str, object]]:
    events = _events()
    typed, click, page = (
        copy.deepcopy(events[1]),
        copy.deepcopy(events[3]),
        copy.deepcopy(events[4]),
    )
    typed["gesture"].update(kind="type", value=_TYPED, secret=False)
    typed["gesture"]["target"] = {**typed["gesture"]["target"], "secret": False}
    click["gesture"]["outline"] = _FORGED
    click["gesture"]["snapshot"] = _FORGED
    click["outlines"] = [_FORGED]
    page["outlines"] = [_FORGED]
    click["gesture"]["outlines"] = [
        {
            "headings": [
                "Customer Types",
                "access_token=live-token",
                f"Open /reset/{_PATH_TOKEN} to continue",
            ],
            "landmarks": [
                {"role": "form", "name": "New"},
                {"role": "region", "name": "Anything"},
                {"role": ["form"], "name": "Unhashable"},
            ],
            "fields": [
                {"role": "textbox", "label": "Verify", "value": _OTP, "required": True},
                {"role": "gridcell", "label": "Row 4"},
                {"role": [], "label": "A list role"},
                {"role": {}, "label": "A mapping role"},
                {"role": "combobox", "label": "Department", "options": ["Finance", _A_JWT]},
                {"role": "combobox", "label": "Carrier", "options": [f"c{i}" for i in range(26)]},
            ],
            "buttons": ["Save"],
            "messages": [
                {"role": "status", "text": "https://wms.example/cb?access_token=live-token"},
                {"role": "alert", "text": f"Code {_OTP} has expired"},
                {"role": "status", "text": f"Verifying {_SECRET}"},
                {"role": "banner", "text": "free page text"},
                {"role": ["alert"], "text": "a list role"},
            ],
            "value": _OTP,
            "text": f"all page text {_TYPED}",
        }
    ]
    return [typed, click, page]


async def test_a_client_that_sends_values_in_an_outline_stores_none_of_them() -> None:
    uow = FakeUnitOfWork()
    blobs = FakeBlobStore()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_hostile_outline"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=_hostile_outline(),
    )

    assert stored.stored_at is not None
    written = (await blobs.read(stored.stored_at)).decode("utf-8")
    (outline,) = next(
        one.action.outlines for one in uow.gestures.rows.values() if one.action.outlines
    )
    kept = repr(outline)
    for said in (
        _OTP,
        _SECRET,
        _A_JWT,
        _PATH_TOKEN,
        "live-token",
        "free page text",
        "all page text",
        "Row 4",
        "Anything",
        "A list role",
        "A mapping role",
        "a list role",
        "Unhashable",
        "has expired",
        "Forged Under Another Key",
    ):
        assert said not in written, f"{said!r} reached the evidence blob"
        assert said not in kept, f"{said!r} reached an outline in the gesture store"
    assert outline.headings == ("Customer Types",)
    assert outline.landmarks == (Landmark("form", "New"),)
    assert [(one.role, one.label, one.options) for one in outline.fields] == [
        ("textbox", "Verify", None),
        ("combobox", "Department", ("Finance",)),
        ("combobox", "Carrier", None),
    ]
    assert outline.buttons == ("Save",)
    assert outline.messages == (
        OutlineMessage("status"),
        OutlineMessage("alert"),
        OutlineMessage("status"),
    )


def test_a_word_the_operator_typed_is_still_the_screen_s_vocabulary() -> None:
    typed = {"kind": "gesture", "tab_id": 1, "gesture": {"kind": "type", "at": 1.0}}
    typed["gesture"]["value"] = "Operations Center"
    click = {"kind": "gesture", "tab_id": 1, "gesture": {"kind": "click", "at": 2.0}}
    click["gesture"]["outlines"] = [
        {
            "headings": ["Operations Dashboard", "Picking", "Step 1 of 3"],
            "fields": [
                {"role": "textbox", "label": "Pick Location"},
                {"role": "combobox", "label": "Site", "options": ["Operations Center", "Dock"]},
            ],
            "buttons": ["Reopen"],
        }
    ]

    (_, out) = redact_events([typed, click])

    (outline,) = out["gesture"]["outlines"]
    assert outline["headings"] == ["Operations Dashboard", "Picking", "Step 1 of 3"]
    assert [one["label"] for one in outline["fields"]] == ["Pick Location", "Site"]
    assert outline["fields"][1]["options"] == ["Operations Center", "Dock"]
    assert outline["buttons"] == ["Reopen"]


def test_an_outline_too_large_to_send_loses_its_option_lists_before_its_fields() -> None:
    options = [f"Carrier option number {i:02d} with a long name" for i in range(K_OUTLINE_OPTIONS)]
    fields = [
        {"role": "combobox", "label": f"Carrier {i}", "options": options}
        for i in range(K_OUTLINE_FIELDS)
    ]
    click = {"kind": "gesture", "tab_id": 1, "gesture": {"kind": "click", "at": 2.0}}
    click["gesture"]["outlines"] = [
        {"headings": ["Carriers"], "fields": fields, "buttons": ["Save"]}
    ]

    ((out,),) = [one["gesture"]["outlines"] for one in redact_events([click])]

    assert len(json.dumps(out, separators=(",", ":"))) <= K_OUTLINE_CHARS
    assert out["headings"] == ["Carriers"]
    assert out["fields"][0]["options"] == options
    assert out["fields"][-1] == {
        "role": "combobox",
        "label": f"Carrier {K_OUTLINE_FIELDS - 1}",
        "required": None,
        "options": None,
    }
    assert len(out["fields"]) == K_OUTLINE_FIELDS, "labels outlast option lists"
    kept = [one for one in out["fields"] if one["options"] is not None]
    assert kept == out["fields"][: len(kept)], "option lists are dropped from the end"


def test_an_outline_too_large_to_send_keeps_all_its_fields_while_it_drops_headings() -> None:
    long = " ".join(["word"] * 20)
    headings = [f"{long} {i:03d}" for i in range(K_OUTLINE_FIELDS)]
    buttons = [f"{long} {i:03d}" for i in range(K_OUTLINE_FIELDS)]
    landmarks = [{"role": "dialog", "name": f"{long} {i:03d}"} for i in range(K_OUTLINE_FIELDS)]
    fields = [
        {"role": "textbox", "label": f"Field {i}", "options": None} for i in range(K_OUTLINE_FIELDS)
    ]
    click = {"kind": "gesture", "tab_id": 1, "gesture": {"kind": "click", "at": 2.0}}
    click["gesture"]["outlines"] = [
        {"headings": headings, "buttons": buttons, "landmarks": landmarks, "fields": fields}
    ]

    ((out,),) = [one["gesture"]["outlines"] for one in redact_events([click])]

    assert len(json.dumps(out, separators=(",", ":"))) <= K_OUTLINE_CHARS
    assert len(out["fields"]) == K_OUTLINE_FIELDS, "fields survive the trim intact"
    assert len(out["headings"]) < K_OUTLINE_FIELDS, "headings are dropped before fields"


def test_a_tree_from_an_older_extension_is_discarded_unread() -> None:
    event = {"kind": "snapshot", "snapshot": {"nodes": [{"name": "Service Level"}]}}

    (out,) = redact_events([event])

    assert "snapshot" not in out
