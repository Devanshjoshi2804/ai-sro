"""A password is not evidence of what happened; it is a key to the customer's
system, and a body that kept one turns the evidence store into a credential
store with none of the handling that implies.

Request bodies were always cleaned. Response bodies had two ways round it, and
both of them reported no fields removed afterwards -- which reads as "there
were none".
"""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

from sro.domain.recording.network import Body
from sro.infrastructure.steel.capture import CaptureSession, _PendingRequest
from tests.unit.fakes import FakeBlobStore

SECRET = {"user": "clerk", "password": "hunter2"}  # the thing under test


class _Cdp:
    """Just the one call `_response_body` makes."""

    def __init__(self, body: str, *, base64_encoded: bool) -> None:
        self._answer = {"body": body, "base64Encoded": base64_encoded}

    async def send(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._answer


def _session(blobs: FakeBlobStore, *, inline_limit: int = 256 * 1024) -> CaptureSession:
    session = CaptureSession(
        blob_store=blobs,
        key_prefix="acme/rec-1",
        inline_body_limit_bytes=inline_limit,
        video=False,
    )
    return session


def _pending() -> _PendingRequest:
    pending = object.__new__(_PendingRequest)
    object.__setattr__(pending, "mime_type", "application/json")
    return pending


async def _captured(
    body: str, *, base64_encoded: bool = False, inline_limit: int = 256 * 1024
) -> tuple[Body | None, FakeBlobStore]:
    blobs = FakeBlobStore()
    session = _session(blobs, inline_limit=inline_limit)
    session._cdp = _Cdp(body, base64_encoded=base64_encoded)  # type: ignore[assignment]
    return await session._response_body("req-1", _pending()), blobs


async def test_a_json_response_loses_the_password_it_carried() -> None:
    body, _ = await _captured(json.dumps(SECRET))

    assert body is not None
    assert "hunter2" not in (body.text or "")
    assert body.redacted_fields == ("password",)


async def test_a_response_the_browser_handed_back_as_base64_is_cleaned_too() -> None:
    """CDP base64-encodes whatever it cannot give back as a UTF-8 string, which
    is a screenshot *and* a JSON document served with a charset it would not
    guess at. The second kind has field names in it, and was skipped."""
    encoded = base64.b64encode(json.dumps(SECRET).encode()).decode()

    body, _ = await _captured(encoded, base64_encoded=True)

    assert body is not None
    assert "hunter2" not in (body.text or "")
    assert body.redacted_fields == ("password",)
    # Rewritten, so it is text now: nothing is gained by re-encoding a document
    # we have just had to parse, and a reviewer can read this one.
    assert body.encoding is None


async def test_a_body_too_large_to_inline_is_cleaned_before_it_is_stored() -> None:
    """The bigger hole. A body over the limit went to object storage exactly as
    it arrived, so the one response big enough to be interesting was the one
    whose credentials were kept."""
    padded = {**SECRET, "rows": ["x" * 200] * 20}

    body, blobs = await _captured(json.dumps(padded), inline_limit=64)

    assert body is not None and body.blob_uri is not None
    assert body.redacted_fields == ("password",)
    stored = await blobs.read(body.blob_uri)
    assert b"hunter2" not in stored


async def test_a_genuinely_binary_response_is_left_exactly_as_it_was() -> None:
    """A screenshot has no field names in it. Decoding it as text would fail,
    and pretending otherwise is how binary evidence gets corrupted."""
    png = b"\\x89PNG\\r\\n\\x1a\\n\\xff\\xfe" + bytes(range(200, 256))
    encoded = base64.b64encode(png).decode()

    body, _ = await _captured(encoded, base64_encoded=True)

    assert body is not None
    assert body.encoding == "base64"
    assert body.text == encoded
    assert body.redacted_fields == ()


@pytest.mark.parametrize("base64_encoded", [False, True])
async def test_a_body_with_nothing_secret_in_it_is_untouched(base64_encoded: bool) -> None:
    plain = json.dumps({"workArea": "SROTEST1", "priority": 2})
    sent = base64.b64encode(plain.encode()).decode() if base64_encoded else plain

    body, _ = await _captured(sent, base64_encoded=base64_encoded)

    assert body is not None
    assert body.text == sent
    assert body.redacted_fields == ()
