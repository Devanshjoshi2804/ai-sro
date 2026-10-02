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

docker build --build-context page=new-chrome-extension/src/page \
  -t ai-sro-backend:$REV --build-arg REVISION=$REV backend/

docker build -t ai-sro-web:$REV \
  --build-arg NEXT_PUBLIC_API_URL=http://10.11.9.25:8000 \
  --build-arg NEXT_PUBLIC_EXTENSION_ORIGINS=chrome-extension://onfmljaebeipeiinflhgdochbcjeoehl,chrome-extension://fokdlimdngfkjpnpeogpeeldcoikabpj \
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

**There are two ids, and both must be listed** (comma-separated here, a JSON
list in `SRO_CORS_ORIGINS`): `onfmljae...` is the unpacked build, pinned by the
manifest `key`; `fokdlimdng...` is the Chrome Web Store item, whose key the
store issues. Drop either and that build's panel connects to nothing.

**Publishing the extension:** `make gen-deployment api=... console=...`, then
`make package-extension`, then upload `dist/ai-sro-<version>.zip` on the item's
Package tab. The zip carries no manifest `key` (the store adds its own) and no
tests. Raise `version` in `new-chrome-extension/manifest.json` first: the store
refuses a version it already has.

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

## Changing the proxy's config

`infra/Caddyfile` is mounted from a directory, not as a single file, and the
reason is worth keeping: a single-file bind mount binds an inode, `git pull`
replaces the file rather than writing through it, and the container goes on
serving the config it started with. `compose up -d` will not notice, because
the service definition has not changed. After editing it:

```bash
$C up -d --force-recreate caddy    # or `$C restart caddy` for a live reload
```

Check what is actually loaded rather than what is on disk:

```bash
$C exec caddy caddy validate --config /etc/caddy/Caddyfile
```

## The vault's directory, once per volume

Docker creates a missing mount point as root, so `vault-data` arrives
`root:root` on a deployment whose image did not already have `/var/lib/sro` --
and the containers run as uid 10001 and cannot become root. Every attempt to
store a credential then answers `PermissionError: /var/lib/sro/vault.tmp`.
Nothing notices until the first secret: found on QA 2026-09-16, where the vault
file had never been written at all.

The image now creates the directory owned by `sro`, which is enough for a
volume made after that. One that already exists keeps the ownership it has:

```bash
$C run --rm --user root --entrypoint sh api -c 'chown -R 10001:10001 /var/lib/sro'
```

## Migrating QA's vault keys to the S1 scheme (one shot)

S1 moved vault keys from `{tenant}/{credential origin}/password` to
`{tenant}/{credential origin}/{username}/password`. QA's existing passwords
are under the old key, so `backend/scripts/migrate_vault_keys.py` copies each
one to the new key it belongs at, read off the tenant's recorded sign-in job.
It never deletes the old key on its own and never prints a secret value.

```bash
make migrate-vault-keys                       # dry-run: prints what it would do
make migrate-vault-keys apply=1                # copies old keys to new ones on QA
make migrate-vault-keys apply=1 delete-old=1   # only after QA-1 has passed
```

Run the dry-run first, read its output, then `apply=1`. Run `apply=1
delete-old=1` only once QA-1 has passed on the copied keys — it is a separate
run so the old keys stay in place as a rollback until then.

## After every deploy

```bash
make smoke at=http://10.11.9.25:8088 DOCKER="sudo docker"
```

`DOCKER="sudo docker"` because nobody on that host is in the `docker` group,
and adding somebody to it grants root on a machine three other teams share.
`env=infra/.env.prod` picks the other environment.

It asks the one question a test suite cannot: whether the urls this system
hands to a browser name anything a browser can reach. It runs inside the API
container, because it needs the app's own adapters to mint those urls, and
then it uses them over the public address the way a page would -- fetching a
presigned artifact, opening a real browser session, loading its live view and
reading a frame off the screencast socket. Exit 1 and the name of what is
wrong, or exit 0.

Every defect found on the first day of deploying was on one of those edges,
and every one looked correct in the code and worked on a laptop. Read the
docstring in `backend/scripts/smoke.py` for the list; it is the argument for
the script.

## Steel needs a container recreate, once

`steel`'s compose definition now sets `NODE_OPTIONS=--unhandled-rejections=warn`
(see `.superpowers/sdd/2026-09-24-execution-runtime/task-S5-rereview-1.md`,
"Second crash path"): a tab that closes before Steel's own new-target handler
finishes its awaited CDP calls -- a self-closing sign-in popup can trigger
this the same way our own `close_tab` can -- otherwise leaves an unhandled
rejection Steel never catches, and Node exits, killing every account sharing
that container. Docker only applies an environment change to a container it
recreates, not one it restarts, so QA's `steel` service needs one recreate at
the next deploy:

```bash
docker compose -f infra/docker-compose.deploy.yml up -d --no-deps steel
```

Never add `-f docker-compose.yml` to that command: the QA box uses only the
deploy file, and the base file's ports collide with the box's own Postgres.
Every live QA session on that container is lost when it recreates, same as
any Steel restart; release it and start over once the new container is
healthy.

## Nango (mail accounts connected with one click)

Self-hosted Nango (free tier: OAuth, token refresh, proxy; no Elasticsearch or
S3) runs beside AI-SRO. Its data is the database `nango` on our Postgres,
owned by its own role `nango`; it never touches `sro`. Reference:
<https://nango.dev/docs/guides/platform/self-hosting>.

**Not under `/nango`.** The dashboard is served from the root and has no
sub-path setting, so it gets its own proxy port, 8089 (`NANGO_BIND`), and the
Connect UI (the popup the console opens) gets 8082 (`NANGO_CONNECT_BIND`), both
routed by `infra/Caddyfile`. **Both bind to loopback by default**: the
dashboard holds the environment secret key and every connected mailbox's
grant, over plain HTTP, on a shared box. Reach them by SSH tunnel:

```bash
ssh -L 8089:127.0.0.1:8089 -L 8082:127.0.0.1:8082 <user>@10.11.9.25
```

Use `0.0.0.0:<port>` in the env file only once TLS and a hostname exist.

**Before pulling this change on the box**, edit `.env.qa`: the new
`NANGO_*` variables are required, so every `docker compose` command fails until
they are set. Add `NANGO_DB_USER=nango`, `NANGO_DB_PASSWORD`,
`NANGO_ENCRYPTION_KEY` (`openssl rand -base64 32`; never change it
afterwards), `NANGO_PUBLIC_URL`, `NANGO_PUBLIC_CONNECT_URL`,
`NANGO_DASHBOARD_USERNAME` and `NANGO_DASHBOARD_PASSWORD`.

**The redirect URI.** The OAuth redirect happens in the operator's browser,
and Nango's callback is `<NANGO_PUBLIC_URL>/oauth/callback`. Pick one:

- Tunnel: `NANGO_PUBLIC_URL=http://localhost:8089` and
  `NANGO_PUBLIC_CONNECT_URL=http://localhost:8082`. Register
  `http://localhost:8089/oauth/callback` in the Azure app. Check in the Azure
  portal that it accepts an `http://localhost` redirect URI before relying on
  this.
- Once TLS and a hostname exist: `NANGO_PUBLIC_URL=https://nango.<host>`, a
  matching https Connect URL, and register `https://nango.<host>/oauth/callback`.

Register this redirect URI in the Azure app: `<NANGO_PUBLIC_URL>/oauth/callback`
with the value you set. A plain `http://10.11.9.25:8089/...` address will not
do (Azure takes http redirect URIs for localhost only; check in the portal).

**What the backend needs.** Set these in the env file (the deploy compose passes
them to the api container):

- `SRO_NANGO_URL`: where the backend reaches Nango inside the compose network,
  `http://nango-server:8080`.
- `SRO_NANGO_SECRET_KEY`: the environment secret key from the Nango dashboard
  (Environment Settings). Leave it blank until Nango is up. A wrong key shows
  "Connections are misconfigured on this server" and the api log says 401.
- `SRO_NANGO_PUBLIC_URL` and `SRO_NANGO_PUBLIC_CONNECT_URL`: the same two
  addresses as `NANGO_PUBLIC_URL` and `NANGO_PUBLIC_CONNECT_URL`, which the
  console hands to the popup.
- `SRO_INTEGRATIONS`: the integrations the Connections page offers, as a JSON
  list of Nango integration ids, for example `["microsoft"]`. Each id must also
  exist in Nango.
- `SRO_CONNECTOR_SIGNING_KEY` (`openssl rand -hex 32`): signs the per-operator key
  stored when an operator connects an account; the mail connector verifies it with
  the same value. At least 32 bytes, or the server refuses to start. Unset or
  blank, linking answers 503 and nothing counts as connected. Changing it makes
  every stored key stale until each operator presses Connect again. A Nango
  disconnect revokes the connector's access: the connector must still find a
  healthy Nango connection, the stored key alone is not authority.

**Console SDK call.** The browser loads the popup from the Connect URL and the
popup calls the server URL, so the console passes both:
`nango.openConnectUI({ baseURL: <NANGO_PUBLIC_CONNECT_URL>, apiURL: <NANGO_PUBLIC_URL> })`
(<https://nango.dev/docs/reference/frontend/frontend-sdk>).

**Database.** A fresh Postgres volume creates the `nango` role and database
from `infra/init-db.sh`. On the existing QA volume (the init script does not
run on an existing one), once. Export the variables in your shell and pass them
into the running container, so Postgres is not recreated:

```bash
set -a; . infra/.env.qa; set +a
docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa \
  exec -T -e NANGO_DB_USER -e NANGO_DB_PASSWORD postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v nu="$NANGO_DB_USER" -v np="$NANGO_DB_PASSWORD"' <<'SQL'
CREATE ROLE :"nu" LOGIN PASSWORD :'np';
CREATE DATABASE nango OWNER :"nu";
SQL
```

Then start it, and recreate Caddy to publish the new ports:

```bash
docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa \
  up -d --no-deps nango-redis nango-server
docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa \
  up -d --no-deps --force-recreate caddy      # a new published port needs a recreate
```

Open the dashboard through the tunnel (`http://localhost:8089`) and sign in
with the basic-auth credentials. Create the integration `microsoft`: client id
and secret from the Azure app registration, scopes
`offline_access Mail.Read Mail.ReadWrite Mail.Send User.Read`. Copy the
environment secret key (Environment Settings) into `.env.qa` as
`SRO_NANGO_SECRET_KEY`. `SRO_NANGO_URL` stays `http://nango-server:8080`.

**Upgrading Nango.** The image is pinned (`nangohq/nango-server:hosted-<version>`,
tags on Docker Hub, versions on <https://github.com/NangoHQ/nango/releases>)
and so is Redis. To upgrade, edit the tag in `infra/docker-compose.deploy.yml`,
read the release notes, and `up -d --no-deps nango-server`.

## Outlook

`outlook-connector` is the Gmail connector's twin: the same five tools and the
same answers, read from Microsoft Graph through Nango's proxy. It holds no
Microsoft token. It is behind the `outlook` compose profile, because the Nango
secret key it needs can only be read from Nango's dashboard once Nango is up.
Order: boot `nango-server`; read the secret key from its dashboard; set
`SRO_NANGO_SECRET_KEY` and `SRO_CONNECTOR_SIGNING_KEY` (the connector reads the
same value as `CONNECTOR_SIGNING_KEY`; under 32 bytes it will not start and says
so); `docker compose --profile outlook up -d outlook-connector`; then add
`outlook=http://outlook-connector:8934/mcp` to `SRO_MCP_SERVERS` (see
`infra/.env.deploy.example`). Neither key is required for any other service.

- **Who may call:** the signed bearer the backend writes when an operator presses
  Connect on Outlook. No grants file, no volume.
- **Whose mailbox:** the newest healthy Nango connection tagged with that
  operator. It is remembered for a minute; a disconnect in Nango ends access
  within that minute and the call gets the same "no grant" answer a bad bearer
  gets.
- **Queries:** the Gmail query is translated. Dates, folders (`in:sent`),
  `is:unread` and `has:attachment` become `$filter` (and `$orderby` when the filter has a date bound). Words, `from:`,
  `to:`, `subject:` become `$search` (KQL), and Graph refuses `$filter` and
  `$orderby` beside it, so a search's date window and unread state are applied to
  the page that came back. A phrase searches as all of its words. `-in:chats` is
  dropped; mail in Deleted Items and Junk is never returned unless `in:anywhere`.
- **Sending:** a mail is made as a draft carrying the `X-SRO-Marker` header (Graph
  sets custom headers only at creation), then sent; `send_message` answers the
  draft's id. Every Graph call asks for immutable ids
  (`Prefer: IdType="ImmutableId"`), so that id is the Sent Items copy's id and no
  folder move changes it. A reply is a `createReply` draft of the mail whose
  Message-Id is `in_reply_to`, else the newest of `thread_id`. Not verified against
  a live mailbox: that `createReply` keeps `message.internetMessageHeaders`.
- **Health:** the container's check is a TCP connect to 8934 (the Gmail one, 8932).
  Before this, both inherited the image's check on the API's port 8000 and were
  `unhealthy` from the start.

## Which mail connector a tenant is on

`SRO_MAIL_SERVERS` is a JSON object from tenant id to connector name, e.g.
`'{"acme": "outlook"}'`; a tenant not listed is on `gmail`. A name is lowercase
letters, digits, `_` or `-`, and anything else stops the settings load.

Switch a tenant only when none of its runs is waiting on a mail. A run records
the server its mail is on (`awaiting.server`) when it starts, so one already
waiting when the setting changes keeps looking for its answer on the old server
and is never matched to a reply on the new one. Let those runs finish or stop
them first.

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

**Point the extension at this deployment before handing it to anybody:**

```bash
make gen-deployment api=http://10.11.9.25:8088/api console=http://10.11.9.25:8088
```

It writes `new-chrome-extension/src/background/deployment.generated.js`, and
the operator then pastes a credential and nothing else — the addresses are
filled in and folded away behind *Addresses*. They used to be two empty fields
with `localhost` placeholders, which are wrong on every machine but a
developer's, and getting one wrong presents as "cannot reach the deployment"
rather than as a typo.

The extension has no build step, so **what is in the tree is what gets
loaded**: a QA build and a production build differ by that one generated file,
and whichever was generated last is what a `git pull` gives the next person.
Regenerate after switching environments. The suite reads the constant rather
than hardcoding an address, so it passes whichever deployment the file names.

It remains a default and not a lock: sign-in still takes whatever url is
typed, so one build can be pointed elsewhere without regenerating.

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
