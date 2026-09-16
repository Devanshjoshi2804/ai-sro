# The API and the Temporal worker. One image, two commands.
#
# They are one image because they are one codebase and must be one build: a
# skill is induced in the worker and read by the API, and a worker running
# last week's code against this week's rows is the failure `docs/CONTEXT.md`
# §8 opens with. One image makes the two impossible to skew by accident, and
# `docker compose up` restarts both from the same digest.
#
#     docker build -t ai-sro-backend:$(git rev-parse --short HEAD) backend/
#
# Build it with `--build-arg REVISION=$(git rev-parse --short HEAD)`. The
# settings read `SRO_REVISION` first and fall back to asking git, which a
# container cannot do -- it ships without a `.git` -- and the fallback answers
# "unknown". A deployment that cannot say which commit it is running is one
# nobody can debug.

FROM python:3.12-slim AS build

# uv, pinned. A build that resolves a different uv every time resolves
# different wheels every time, and `uv.lock` exists to stop exactly that.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# The lock alone first, so a change to source does not re-resolve the world.
# `--no-install-project` because the project itself is the layer that changes.
COPY pyproject.toml uv.lock ./
# `--extra gcp` because a deployment keeps its secrets in Secret Manager, and
# an image without the client refuses at the first password a run tries to
# type -- which is a deploy-time surprise on the one path that cannot be
# retried by hand. The extra is optional in `pyproject` so a laptop and the
# test suite do not carry it; the image is where it stops being optional.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --extra gcp

COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
# The operational scripts travel with the image that runs them. `smoke.py`
# has to execute where the app's own adapters are, and a deployment that
# cannot run its own post-deploy check because the check lives in a checkout
# somebody forgot to pull is a check that does not exist. `measure.py` and
# `open_joins.py` are here for the same reason.
COPY scripts ./scripts
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra gcp


FROM python:3.12-slim AS runtime

# curl for the healthcheck, and nothing else. Every other package is a
# vulnerability report somebody has to read.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 sro

# The vault's directory, owned by the user that has to write it.
#
# Docker creates a missing mount point as root, so a named volume mounted at a
# path the image does not have arrives `root:root` and this container -- which
# runs as uid 10001 and cannot become root, deliberately -- cannot write a
# thing into it. Every attempt to store a credential answered `PermissionError:
# /var/lib/sro/vault.tmp`, and nothing had noticed because nothing on that
# deployment had ever stored one: the vault file did not exist at all.
#
# Created here rather than chowned at start-up, because a fresh volume takes
# its ownership from the image's directory. A volume that already exists keeps
# whatever it has and needs the one-off chown by hand -- `docs/18-deployment.md`.
RUN install -d -o sro -g sro -m 0700 /var/lib/sro

WORKDIR /app

COPY --from=build --chown=sro:sro /app/.venv ./.venv
COPY --from=build --chown=sro:sro /app/src ./src
COPY --from=build --chown=sro:sro /app/migrations ./migrations
COPY --from=build --chown=sro:sro /app/alembic.ini ./
COPY --from=build --chown=sro:sro /app/scripts ./scripts

ARG REVISION=unknown
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SRO_REVISION=$REVISION

# Not root, and not able to become root. The container runs a browser's worth
# of untrusted captured payloads through a parser.
USER sro

EXPOSE 8000

# `/health` is the unauthenticated one; everything under `/v1` answers 401
# without a credential, which a healthcheck does not have and should not.
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=4 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# No `--reload`: it watches the filesystem, doubles the process tree, and is a
# development affordance. One worker, because until runs become Temporal
# workflows a single API process owns every run in flight -- the assumption the
# in-process device sockets, the approval register and the startup orphan sweep
# all already make. Raising this without moving those is how an operator's
# Approve lands in a process that is not driving their browser.
CMD ["uvicorn", "sro.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
