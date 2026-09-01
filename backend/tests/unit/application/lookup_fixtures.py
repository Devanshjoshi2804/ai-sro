"""Frames and calls shaped like the carrier cross reference evidence."""

from __future__ import annotations

import json

from sro.domain.recording.network import CapturedRequest
from tests import factories as f


def a_read(url: str, records: list[dict[str, object]] | None = None) -> CapturedRequest:
    """A listing read: a GET answered in WMS's own ``{"data": [...]}`` shape."""
    return f.request(
        method="GET",
        url=url,
        request_body=None,
        response_body=f.body(json.dumps({"data": records or []})),
    )
