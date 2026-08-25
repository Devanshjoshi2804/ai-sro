"""The stub's own WebSocket codec, checked against the RFC's example.

Written after the magic GUID in it was wrong by one character. Nothing failed:
Chrome refused the handshake, closed the connection, and the extension looked
like one that had never dialled. A test at this level says which half is broken.
"""

from __future__ import annotations

import io

from tests.browser.ws import accept_key, decode, encode


def test_the_handshake_key_matches_the_rfc_example() -> None:
    assert accept_key("dGhlIHNhbXBsZSBub25jZQ==") == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="


def test_a_frame_survives_its_own_round_trip() -> None:
    """Three sizes, because the length is encoded three different ways: inline
    under 126 bytes, two bytes up to 64k, eight beyond it. A screenshot answer
    is comfortably in the third."""
    for size in (10, 1_000, 200_000):
        payload = b"x" * size
        opcode, back = decode(io.BytesIO(encode(payload)))
        assert opcode == 1
        assert back == payload


def test_a_masked_frame_is_unmasked() -> None:
    """Everything a browser sends is masked, so a codec that ignored the mask
    would read every command as noise."""
    mask = bytes([0x01, 0x02, 0x03, 0x04])
    payload = b"hello there"
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    frame = bytes([0x81, 0x80 | len(payload)]) + mask + masked
    assert decode(io.BytesIO(frame)) == (1, payload)
