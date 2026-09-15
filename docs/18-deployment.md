# Deployment

How this runs on a machine that is not a laptop. Written for the first real
target: **one VM, QA first, and that QA stack shown to a client as a POC.**

That last part decides the shape of everything below. A QA environment nobody
outside sees can cut corners; one a client is shown cannot, because the corners
are what they will find. So QA runs the production compose file, the production
images and the production switches, and differs from production in its
hostnames and its secrets and nothing else. When QA passes, the **same image
tags** are promoted. An image rebuilt for production is an image nothing tested.

## What actually runs

Four processes and five backing services:

| | what | why it is its own process |
|---|---|---|
| `api` | `uvicorn sro.main:app` | serves the console and every operator's extension |
| `worker` | `python -m sro.infrastructure.temporal.worker` | induction, mining sweeps, retention |
| `web` | `node server.js` | the console |
| `steel` | the browser sandbox | the fallback rung when the operator's own browser is not driving |

plus Postgres + pgvector, MinIO, Temporal, an OTLP collector, and a one-shot
`migrate` that must exit 0 before the API starts.

**The worker is not optional and not the API.** Induction runs there. An
API-only restart silently keeps running last week's code against this week's
rows — the first line of `CONTEXT.md` §8, learned the hard way. The compose
file puts both in one `up -d` from one image so they cannot skew.

## Build

Both images are built from the repo root, tagged with the commit:

```bash
REV=$(git rev-parse --short HEAD)

docker build -t ai-sro-backend:$REV --build-arg REVISION=$REV backend/

docker build -t ai-sro-web:$REV \
  --build-arg NEXT_PUBLIC_API_URL=http://10.11.9.25:8000 \
  --build-arg NEXT_PUBLIC_EXTENSION_ORIGINS=chrome-extension://onfmljaebeipeiinflhgdochbcjeoehl \
  frontend/
```

`REVISION` matters: the settings read `SRO_REVISION` and otherwise ask git,
which a container cannot do. A deployment that cannot name its own commit is
one nobody can debug, and `/health` is where somebody looks first.

**`NEXT_PUBLIC_*` is baked in at build time and cannot be changed at run
time**, so an absolute API url in the bundle is a hostname promised to one
environment. That is why `infra/Caddyfile` exists: behind it the console is
built with `NEXT_PUBLIC_API_URL=/api`, which promises nothing, and **one web
image promotes from QA to production unchanged.**

`NEXT_PUBLIC_EXTENSION_ORIGINS` is still per-build, because it is read in
`headers()` during the build. It is the extension's id, which is the same
everywhere, so it does not divide environments the way a hostname would.

## The VM

Target `10.11.9.25`, reached over OS Login (`docs`: the Confluence page on GCP
OS Login). Access is per-person and per-project:

```bash
gcloud compute os-login describe-profile --format='value(posixAccounts.username)'
ssh -i ~/.ssh/id_rsa <that username>@10.11.9.25
```

A `Permission denied (publickey)` here with a key that OS Login already holds
means the IAM grant is missing, not the key: ask for `roles/compute.osLogin`
(or `osAdminLogin` for sudo) on the project that owns the VM.

On the box:

```bash
# once
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker "$USER"     # log out and back in

# every deploy
git clone <this repo> ~/ai-sro && cd ~/ai-sro     # or git pull
cp infra/.env.deploy.example infra/.env.qa        # fill it in, once
docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa up -d
docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa ps
```

Images reach the VM either by building there or by `docker save | ssh … docker
load`. A registry is better and is the first thing to add when a second
environment exists.

`up -d` is the whole deploy: `migrate` runs to completion first, then `api` and
`worker` start together from the same image.

## Five things that are quiet when wrong

1. **`SRO_API_URL` and `SRO_CONSOLE_URL` default to localhost.** They are not
   cosmetic. `our_own_origins()` reads them to decide which traffic is this
   system's own, and evidence is refused for those origins ahead of any tenant
   policy. Left at their defaults on a VM, the console's own API calls are
   captured and mined as warehouse work. That has happened; `config.py` records
   it.
2. **CORS.** `http://localhost:3000` is added only when `SRO_ENVIRONMENT` is
   `local`. A console on its own hostname must appear in `SRO_CORS_ORIGINS` or
   it loads and fails every request.
3. **`init-db.sh` runs once, on the first boot of an empty Postgres volume.**
   On managed Postgres it never runs: create `temporal` and
   `temporal_visibility` and `CREATE EXTENSION vector` by hand, or Temporal
   will not start and the reason will not be obvious.
4. **The extension's id is pinned by its manifest key**, and that id is in both
   `SRO_CORS_ORIGINS` and the console's `frame-ancestors`. If the Chrome Web
   Store assigns a different id than the unpacked build, both break silently —
   as a side panel whose handshake never completes.
5. **Secrets that cannot be rotated casually.** `SRO_AUTH_SECRET` invalidates
   every credential every operator has pasted; `SRO_VAULT_KEY` makes every
   stored system credential unreadable. Generate once, store outside git,
   back them up with the volumes.

## Giving operators access

```bash
make token tenant=<tenant> principal=<who it is for>
```

`principal=` is required and names a person. Every candidate is
`(principal, signature)` and every pairing rule needs one principal on both
sides, so two names for one human splits their work from itself permanently.
One token per person, and the same name each time.

**Known friction, and the POC's most likely failure.** The extension's options
page asks each operator to type an API url, a console url, and paste a token —
three fields, with `localhost` placeholders. On a client machine the
placeholders are wrong, and getting the url wrong presents as "cannot reach the
deployment" rather than as a typo. Before a client POC, the extension should
ship knowing its deployment — either a generated default beside
`shape.generated.js` (the pattern `make gen-recorder` and `make tokens` already
use) or a single pasted connect string carrying url and token together. This is
not done.

## Looking at it

Logs, the database and the worker's liveness, over SSH:

```bash
cd ~/ai-sro
C="sudo docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa"

$C logs -f api worker                       # live
$C logs --since 1h api | grep -iE "error|exception|traceback"
$C ps                                       # what is up
$C exec postgres psql -U sro -d sro         # the database
```

**Whether the worker is working** is not answered by its container status --
one image serves the API and the worker, and the worker serves no HTTP, so its
inherited healthcheck is disabled. Ask Temporal instead:

```bash
$C exec temporal temporal --address temporal:7233 \
  task-queue describe --task-queue default
```

Pollers listed means alive, and each identity carries the revision it is
running, so a worker left behind by a deploy is visible rather than inferred.

### The three UIs, over a tunnel

They bind to `127.0.0.1` on the host on purpose. This box is shared with other
teams and none of these asks who you are, so they are reached by forwarding
rather than by publishing:

```bash
ssh -L 8080:localhost:8080 -L 9001:localhost:9001 -L 16686:localhost:16686 \
    <your-os-login-user>@10.11.9.25
```

| | | |
|---|---|---|
| http://localhost:8080 | Temporal | runs, retries, why a workflow is stuck |
| http://localhost:9001 | MinIO | the artifacts: event streams, screencasts |
| http://localhost:16686 | Jaeger | traces |

Jaeger keeps spans **in memory**: a restart loses them. That is the right
trade for a QA box and the wrong one for anything that has to be investigated
a week later.

## Not done, named rather than implied

- **TLS.** The stack serves plain HTTP. Fine on a private network for QA;
  terminate TLS in front of it before anything crosses one.
- **Backups.** `postgres-data`, `minio-data` and `vault-data` hold the
  evidence, the artifacts and the system credentials. Nothing backs them up.
- **Alerting.** Nothing tells anybody when something breaks; somebody has to
  go and look. It needs a destination before it needs a tool -- an inbox, a
  Slack channel, an on-call rota -- and that is a decision, not a container.
- **Metrics and logs have no backend.** Traces reach Jaeger; metrics and logs
  still only print. A metrics store is a bigger decision than the collector
  config, and this deployment has not needed one yet.
- **A registry**, so promotion is a tag move rather than a rebuild.
- **Steel's own reachability.** `STEEL_DOMAIN` must be an address a person's
  browser can dial, or the live view sits on "Session connecting..." forever.
  Its CDP port is deliberately *not* published: only the API attaches to it,
  and an open DevTools port is full control of a browser holding warehouse
  credentials.
