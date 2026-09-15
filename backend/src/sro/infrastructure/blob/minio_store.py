"""S3-compatible object storage. MinIO locally, whatever the tenant runs in production.

boto3 is synchronous, so every call is offloaded to a thread. A capture session
writes a screenshot per gesture and the occasional large payload, which is far
below the point where an async S3 client would earn its dependency.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from sro.application.ports.blob import BlobStore


class MinioBlobStore(BlobStore):
    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
        public_endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket

        def client(where: str) -> Any:
            return boto3.client(
                "s3",
                endpoint_url=where,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
                config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
            )

        self._client: Any = client(endpoint_url)
        # A presigned url is the one thing here that leaves the deployment: it
        # is handed to a browser, which has never heard of `minio`. Signed
        # against the address that browser can reach, when they differ --
        # deployed, the store is on a compose network and the operator is not.
        # The signature covers the host, so this cannot be a string rewrite
        # afterwards; it has to be signed by a client that knows the address.
        self._signer: Any = client(public_endpoint_url) if public_endpoint_url else self._client

    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self._bucket}/{key}"

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        url: str = await asyncio.to_thread(
            self._signer.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=int(expires_in.total_seconds()),
        )
        return url

    async def presigned_url_for_uri(self, uri: str, *, expires_in: timedelta) -> str | None:
        prefix = f"s3://{self._bucket}/"
        if not uri.startswith(prefix):
            return None
        return await self.presigned_url(uri[len(prefix) :], expires_in=expires_in)

    async def read(self, uri: str) -> bytes:
        prefix = f"s3://{self._bucket}/"
        if not uri.startswith(prefix):
            raise KeyError(f"{uri} is not in this store")
        return await self.get(uri[len(prefix) :])

    async def forget(self, uri: str) -> None:
        prefix = f"s3://{self._bucket}/"
        if not uri.startswith(prefix):
            return
        # S3 answers 204 for a key that was never there, which is the
        # idempotence the port promises rather than something to check for.
        await asyncio.to_thread(
            self._client.delete_object, Bucket=self._bucket, Key=uri[len(prefix) :]
        )

    async def list_prefix(self, prefix: str) -> dict[str, int]:
        entries = await asyncio.to_thread(self._list_entries, prefix)
        return {f"s3://{self._bucket}/{key}": size for key, size in entries}

    async def forget_prefix(self, prefix: str) -> int:
        keys = await asyncio.to_thread(self._list_keys, prefix)
        # S3's batch delete takes at most 1000 keys per call.
        for start in range(0, len(keys), 1000):
            chunk = keys[start : start + 1000]
            await asyncio.to_thread(
                self._client.delete_objects,
                Bucket=self._bucket,
                Delete={"Objects": [{"Key": key} for key in chunk]},
            )
        return len(keys)

    def _list_keys(self, prefix: str) -> list[str]:
        return [key for key, _ in self._list_entries(prefix)]

    def _list_entries(self, prefix: str) -> list[tuple[str, int]]:
        paginator = self._client.get_paginator("list_objects_v2")
        return [
            (entry["Key"], int(entry.get("Size", 0)))
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix)
            for entry in page.get("Contents", [])
        ]

    async def get(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=key
            )
        except ClientError as missing:
            # The port's contract for "not there" is `KeyError` -- the fake
            # raises it because that is what a dict does, and every caller
            # (the miner, a teach reading a batch that aged out mid-sweep) is
            # written against that, not against botocore's own exception.
            code = missing.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "404"):
                raise KeyError(key) from missing
            raise
        body: bytes = response["Body"].read()
        return body
