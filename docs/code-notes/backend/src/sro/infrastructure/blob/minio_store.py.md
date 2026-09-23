# Notes for `backend/src/sro/infrastructure/blob/minio_store.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/blob/minio_store.py`](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py#L1): Docstring

> S3-compatible object storage. MinIO locally, whatever the tenant runs in production.
>
> boto3 is synchronous, so every call is offloaded to a thread. A capture session
> writes a screenshot per gesture and the occasional large payload, which is far
> below the point where an async S3 client would earn its dependency.

## `MinioBlobStore.__init__`, [line 38](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py#L38): Comment

Code: `self._signer: Any = client(public_endpoint_url) if public_endpoint_url else self._client`

> A presigned url is the one thing here that leaves the deployment: it
> is handed to a browser, which has never heard of `minio`. Signed
> against the address that browser can reach, when they differ --
> deployed, the store is on a compose network and the operator is not.
> The signature covers the host, so this cannot be a string rewrite
> afterwards; it has to be signed by a client that knows the address.

## `MinioBlobStore.forget`, [line 75](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py#L75): Comment

Code: `await asyncio.to_thread(`

> S3 answers 204 for a key that was never there, which is the
> idempotence the port promises rather than something to check for.

## `MinioBlobStore.forget_prefix`, [line 85](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py#L85): Comment

Code: `for start in range(0, len(keys), 1000):`

> S3's batch delete takes at most 1000 keys per call.

## `MinioBlobStore.get`, [line 111](../../../../../../../backend/src/sro/infrastructure/blob/minio_store.py#L111): Comment

Code: `code = missing.response.get("Error", {}).get("Code")`

> The port's contract for "not there" is `KeyError` -- the fake
> raises it because that is what a dict does, and every caller
> (the miner, a teach reading a batch that aged out mid-sweep) is
> written against that, not against botocore's own exception.
