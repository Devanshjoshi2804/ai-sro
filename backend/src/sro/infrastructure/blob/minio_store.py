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
    ) -> None:
        self._bucket = bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

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
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=int(expires_in.total_seconds()),
        )
        return url

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        body: bytes = response["Body"].read()
        return body
