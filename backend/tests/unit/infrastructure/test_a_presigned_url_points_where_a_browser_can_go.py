"""A presigned url is the one thing this store hands to somebody else.

Everything else `MinioBlobStore` does is between this process and the object
store, and both are on the same private network. A presigned url is different:
it goes into an API response, the console puts it in an `<img>` or a `<video>`,
and it is fetched by a browser on somebody's laptop.

Deployed, that browser has never heard of `minio`. Every screenshot and every
screencast in the console pointed at `http://minio:9000/...`, which resolves on
the compose network and nowhere a person is sitting, and each one failed as a
broken image rather than as an error anybody saw.

Signing is offline -- boto3 computes the signature without asking the store
anything -- so these need no MinIO.
"""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlsplit

from sro.infrastructure.blob.minio_store import MinioBlobStore

INSIDE = "http://minio:9000"
OUTSIDE = "http://10.11.9.25:9000"


def _store(public: str | None) -> MinioBlobStore:
    return MinioBlobStore(
        endpoint_url=INSIDE,
        access_key="key",
        secret_key="secret",  # noqa: S106 - a signing key for an offline signature
        bucket="sro-artifacts",
        public_endpoint_url=public,
    )


async def test_it_is_signed_against_the_address_a_browser_can_reach() -> None:
    url = await _store(OUTSIDE).presigned_url("shot.png", expires_in=timedelta(minutes=5))

    assert urlsplit(url).netloc == "10.11.9.25:9000"
    assert "minio:9000" not in url, "the private name reached a browser"


async def test_the_signature_covers_the_host_so_rewriting_it_afterwards_would_not_work() -> None:
    """Why this is a second client rather than a `str.replace` on the way out.

    The host is part of what is signed. A url signed for `minio:9000` and then
    edited to say something else is a url MinIO rejects -- so the two differ in
    their signature, not only in their text.
    """
    inside = await _store(None).presigned_url("shot.png", expires_in=timedelta(minutes=5))
    outside = await _store(OUTSIDE).presigned_url("shot.png", expires_in=timedelta(minutes=5))

    def signature(url: str) -> str:
        return dict(pair.split("=", 1) for pair in urlsplit(url).query.split("&"))[
            "X-Amz-Signature"
        ]

    assert signature(inside) != signature(outside)


async def test_one_address_is_still_one_address() -> None:
    """A laptop, where the store is reached by the same name either way. This
    is the only case that was ever exercised before, and it must not change."""
    url = await _store(None).presigned_url("shot.png", expires_in=timedelta(minutes=5))

    assert urlsplit(url).netloc == "minio:9000"
