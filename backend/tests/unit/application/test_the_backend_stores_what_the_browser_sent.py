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
    # Spec §5.6: this page holds a password field, so it is a sign-in page and
    # is stored structure-only -- the username typed into it goes the way the
    # password does, and what was acted on stays.
    assert after[1]["gesture"]["value"] is None
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


def test_a_key_rendered_on_screen_does_not_survive_the_snapshot_tree() -> None:
    """The accessibility tree is 27MB of this deployment's 59MB evidence plane
    -- every string a page rendered, and nothing guarded it."""
    event = {
        "kind": "snapshot",
        "url": "https://wms.example/settings",
        "snapshot": {
            "nodes": [
                {"role": "text", "name": "eyJhbGciOiJIUzI1NiJ9.eyJhIjoxfQ.c2lnbmF0dXJl"},
                {"role": "text", "name": "Service Level"},
            ]
        },
    }

    out = redact_events([event])[0]

    assert "eyJhbGciOiJIUzI1NiJ9" not in json.dumps(out)
    assert out["snapshot"]["nodes"][1]["name"] == "Service Level", "real page text is untouched"


def test_the_snapshot_tree_keeps_its_own_vocabulary() -> None:
    """`token` and `tokenList` are CDP AXValue TYPE descriptors and this corpus
    holds 2,573 of them. A name rule here would blank the tree's structure for
    no protection -- the same trap as `pin` inside `shippingPhone`, and a
    locator is built from exactly these fields."""
    event = {
        "kind": "snapshot",
        "snapshot": {"nodes": [{"type": "token", "name": "Dock"}, {"type": "tokenList"}]},
    }

    nodes = redact_events([event])[0]["snapshot"]["nodes"]

    assert nodes[0]["type"] == "token"
    assert nodes[1]["type"] == "tokenList"
    assert nodes[0]["name"] == "Dock"
