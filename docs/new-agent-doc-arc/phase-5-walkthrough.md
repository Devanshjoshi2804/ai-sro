# Phase 5's live walkthrough

The half of phase 5's acceptance that no agent can perform.

The spec's phase-5 line
([`2026-09-07-the-rig-into-the-backend-design.md:287`](../superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md))
asks for two things. The first — "the ten node suites" — is done, corrected to
25, and green. The second is this:

> a browser signed in once registers, uploads, is served shapes, is offered,
> runs, approves.

It needs a Chrome signed into a real warehouse system and a person to press the
buttons. So it is written here as steps somebody follows, each with the check
that proves it happened, rather than as a script.

---

## Why this is not a formality

Four tables have never held a row. Measured against the store on 2026-09-10:

```sql
select 'workflow_runs' as t, count(*) from workflow_runs
union all select 'workflow_run_steps', count(*) from workflow_run_steps
union all select 'approvals',          count(*) from approvals
union all select 'offers',             count(*) from offers
union all select 'chats',              count(*) from chats;
```

```
 t                  | count
--------------------+-------
 workflow_runs      |     0
 workflow_run_steps |     0
 approvals          |     0
 offers             |     0
 chats              |     0
```
**Re-measured 2026-09-11.** One of the five has been paid:

```
 t                  | count
--------------------+-------
 workflow_runs      |     0
 workflow_run_steps |     0
 approvals          |     0
 offers             |     5
 chats              |     0
```

Five offers, on two tenants, all of them real — three `diverged`, two `expired`,
none `accepted`. So steps 1 to 7 below have now happened in a signed-in Chrome
against the real WMS, and the writes behind them proved out against real
Postgres.

**And then two more, without a browser at all.** `backend/scripts/stub_device.py`
holds the command channel open and answers as a browser would; three dry runs
through it on 2026-09-11 put **`workflow_runs` at 3 and `workflow_run_steps` at
4**, with real model calls behind them — $0.0105 to $0.0274 a run, 7 rows in
`model_calls`. `POST /v1/workflow-runs` answered **201 with the whole row keyed
`id`**, which is the contract step 8 below exists to check, and the backend
accepted every part of it against real Postgres. So the signature failure this
file was written about — a door that is green in 2299 tests and dead against
the real store — is ruled out for the run path by something other than a
promise.

**A fourth stub run, pressed `live: true`, paid one more — 2026-09-11.**
`workflow_runs` to 4, `workflow_run_steps` to 5, and `approvals` off zero for
the first time ever: the run parked on step 1 (`may_write`, `earned` false —
nothing has three held runs yet), `POST /v1/workflow-runs/{id}/approve` was
called, and the write went out (`ui.perform`, `"wrote": true`, a real
`gemini-3.8-flash` call at $0.006813). The run then failed anyway, honestly:
`state unknown after a write; not retried` — the stub's canned answer cannot
show the value this run supplied, so the belt check that reads back a write
correctly refuses to call it held. That failure is the stub's ceiling, not a
defect in the parking gate.

**What this does and does not settle.** The approve call above was made with
the tenant's bare credential, naming no browser — the same door's
"supervisor's console" path, legitimate by the router's own design. The row
it left has `device_id IS NULL`, which is correct for that path and is *not*
the NULL-approver bug this file warns about below (that bug was a call that
meant to send a browser's credentials and silently sent neither). But it is
also not the check steps 8 and 9 exist to run: `approver_is_the_driver`, which
needs an approval sent *as* the driving browser, `?device_id=` and
`X-Device-Secret` together. A stub answering a websocket had no panel to press
Approve from, so that specific check — and a `held` outcome, which needs a
warehouse that can show its own write back — were unproven by anything in
this repository. `approvals` being non-zero was a fact; `approver_is_the_driver`
being `true` was not.

**`approver_is_the_driver` fired for the first time on 2026-09-12.** A stub
holding a command socket already holds the two things a panel proves itself
with — the `device_id` in the URL it dialled and the `X-Device-Secret` it
dialled with — so `scripts/stub_device.py --approve` now sends the pair. It
polls `GET /v1/workflow-runs?awaiting=true`, taps only the runs THIS browser
is driving, and reads the `device_id` off its own socket URL rather than a
flag, so a rig cannot fake the thing it is proving.

A live run of *Create Customer Type DSS* parked on step 1 and the stub
answered it:

```
-> approved run_4e5bafb8c156705f3cffc7a0aaf71e0a step 1 (first: True)
```

```
 run_id                                    | ord | device_id
-------------------------------------------+-----+------------------------------------
 run_015337172df9613f3b03d007b60ed81a       |   1 | NULL          <- console path
 run_a67c0823eb457ff0c4b85978a945bee3       |   1 | NULL          <- console path
 run_4e5bafb8c156705f3cffc7a0aaf71e0a       |   1 | dev_c79a150f… <- a browser
```

The first approval row in this repository's history that names a browser. All
four doors were then tapped against real Postgres over HTTP, and each answered
what the router's docstring says it answers:

| who tapped | answer |
|---|---|
| the browser driving the run | **409** — past the check; that run had already stopped |
| another browser of the same tenant | **403** `not_driving_this_run` |
| the tenant's credential, naming no browser | **409** — the supervisor's console, which skips the check by design |
| `X-Device-Secret` with no `?device_id=` | **404** — half a pair is not a browser |

The 403 is the line that had never been reached. What is still owed is the
browser half: `rigApprove` in a real Chrome, and a `held` outcome, which needs
a warehouse that can show its own write back. The run above failed on its
first step, honestly — the stub cannot read Gmail — which is the stub's
ceiling and not a defect in the gate.

**Re-measured 2026-09-12. All five are paid.**

```
 t                  | count
--------------------+-------
 workflow_runs      |     5
 workflow_run_steps |     4
 approvals          |     2
 offers             |     5
 chats              |     2
```

`chats` was the last one, and it was empty for the reason section 8 gives
below — nothing on this page writes it. It was filled by asking the chat door
what it is for: two real sentences put to `ReadChat` against tenant `new` and
its three mined workflows, on `gemini-3.8-flash`.

- `"create a customer type called ACME"` matched
  `wfl_365d0be081b9cea4e22252529b9e5cb6` — *Create Customer Type DSS* — pulled
  `customertype-customerType = ACME` out of the sentence, and named
  `customertype-longDescription` as the one parameter the operator had not
  given. 805 in / 334 out / 237 thought, $0.001856.
- `"make me a coffee"` matched nothing: `workflow_id` null, no values, nothing
  missing. 802 in / 86 out, $0.000924.

Both are rows. The refusal is billed and recorded exactly like the match,
which is the property the reading path has everywhere else in this rig: the
model was asked, it answered, and the row says what it said.

So what phase 5 still owes, exactly: **steps 8 and 9 pressed by a person, in
their own Chrome, against the real WMS.** Everything before them is paid.


Everything on the execution side — the press, the poll, the offer fate, the
approval — is built, reviewed and mutation-tested. Every one of those tests
fakes `fetch`. They prove what the extension *sends*. Nothing has ever proved
the backend accepts it.

That is this project's signature failure, exactly. `/v1/shapes` and `/v1/spend`
both shipped **dead against real Postgres while 2299 tests were green**, because
`FakeUnitOfWork` exposes its repositories from `__init__` and the real one
assigns them inside `__aenter__`. No unit test could see it. A walkthrough
could.

Phase 5 moved the extension onto one base URL and fixed three calls that would
otherwise have broken at the switchover. Two of the three break *loudly* if the
fix is wrong. **One does not** — see [What would go wrong](#what-would-go-wrong-and-what-it-would-look-like).

---

## Before you start

**One API worker, and only one.** `Approvals`
(`backend/src/sro/application/execution/approvals.py:41`) is an
`asyncio.Event` per parked run, held in the process that is driving the run.
The device sockets are in-process too. Two workers and half the taps land in a
process where nothing is waiting — step 9 would hang and then fail at five
minutes with nobody having done anything wrong. `make api` runs one; keep it
that way.

```bash
make migrate          # head should be 0043
make api              # uvicorn on :8000, single worker, --reload
```

Leave the API's terminal visible. Two of the checks below read its log.

**A tenant with at least one mined workflow that writes.** Step 7 can only
offer a job the store has already proved. `acme` had seven workflows on
2026-09-10; three of them carry parameters. If yours has none, mine first — that
is `POST /v1/mine`, or `backend/scripts/probe_mine_route.py`, and it is not part
of this walkthrough.

**A Chrome you are willing to let type into a live system.** Step 8 starts a
real run against a real warehouse. Step 9 lets a real write out.

### Running the SQL

Every query below is plain SQL and pastes into `psql`:

```bash
psql "$(grep SRO_DATABASE_URL backend/.env | cut -d= -f2- | sed 's/+asyncpg//')"
```

**`psql` was not installed on the machine this was written on.** Every query in
this file was executed against the real store through `asyncpg` instead, using
the pattern from `backend/scripts/probe_mine_route.py`. If you have no `psql`
either, save this as `/tmp/q.py` and run `cd backend && uv run python /tmp/q.py
'select …'`:

```python
import asyncio, os, sys
from pathlib import Path
import asyncpg

def url() -> str:
    u = os.environ.get("SRO_DATABASE_URL")
    if not u:
        for line in Path(".env").open(encoding="utf-8"):
            if line.startswith("SRO_DATABASE_URL="):
                u = line.split("=", 1)[1].strip()
    return u.replace("+asyncpg", "").replace("+psycopg", "")

async def main() -> None:
    conn = await asyncpg.connect(url())
    rows = await conn.fetch(sys.argv[1])
    if rows:
        print(" | ".join(rows[0].keys()))
        for r in rows:
            print(" | ".join(str(v) for v in r.values()))
    else:
        print("(0 rows)")
    await conn.close()

asyncio.run(main())
```

Wherever a query says `:device`, substitute the device id from step 3 — it is
`dev_` and 32 hex characters.

---

## 1. Load the unpacked extension

`chrome://extensions` → Developer mode on → **Load unpacked** →
`new-chrome-extension/`.

Open the options page (**Details** → **Extension options**).

**Check: there are no rig fields any more.** The sign-in card holds exactly
three inputs — *Backend*, *Console* and *Credential*. There is no "Rig URL", no
"Rig token", and the status list has no **Trouble** row fed by a rig refusal.

Proven from the source rather than by squinting at the page:

```bash
grep -c rig new-chrome-extension/src/options/options.html \
           new-chrome-extension/src/options/options.js
```

Both must be `0`. They were not before phase 5: `mirror.js`, `rig-channel.js`,
the rig settings and `rigRegister` are all deleted, and `rig-settings.test.mjs`
went with its subject.

If a rig field is still on the page you are looking at an old build — the
extension directory is stale, or Chrome is serving a cached copy. Reload the
unpacked extension.

## 2. Paste one token

From `backend/`:

```bash
uv run python -m sro.cli.mint acme operator --days 1
```

That prints the token and nothing else. On the options page: **Backend**
`http://localhost:8000`, **Console** `http://localhost:3000`, **Credential** the
token. Save.

**Check: the browser holds a device secret, and none of the three retired keys.**
In the service worker's console (`chrome://extensions` → **service worker**):

```js
chrome.storage.local.get(null).then(held => console.log({
  deviceId:     held["sro.deviceId"],
  hasSecret:    Boolean(held["sro.deviceSecret"]),
  rigUrl:       held["sro.rigUrl"],
  rigToken:     held["sro.rigToken"],
  rigRefusal:   held["sro.rigRefusal"],
}));
```

`deviceId` is a `dev_…` string, `hasSecret` is `true`, and **all three `rig*`
keys are `undefined`**.

They are dropped by `dropRetired()` (`service-worker.js:55`, called at `:58` and
`:65`) from
`RETIRED_KEYS` (`state.js:46`), wired to **both** `onInstalled` **and**
`onStartup`. Both, because MV3 can tear a worker down at any `await`: a browser
that missed the update-time removal gets another chance at every launch, and
removing an absent key is a free no-op. One of those keys matters — on a browser
whose rig could never mint a device token, `sro.rigToken` holds **the tenant's
bearer**, not a device token. Since the keys left `KEYS`, `forget()` no longer
takes them at sign-out, so if `dropRetired` did not run, a spendable tenant
credential would sit in `chrome.storage.local` forever with no door left in this
extension that uses it.

If you are testing on a browser that never had a rig configured, this check
passes trivially. To make it mean something, set the three keys by hand first,
then reload the extension:

```js
chrome.storage.local.set({
  "sro.rigUrl": "http://rig.test",
  "sro.rigToken": "tok-tenant-bearer",
  "sro.rigRefusal": "something",
}).then(() => chrome.runtime.reload());
```

Re-run the read. All three must be gone.

## 3. Registration

Registration is automatic on sign-in: `register()` posts `/v1/agents/register`
and stores the id and the secret it is handed back.

**Check: the row exists and the secret the browser holds is the secret the
backend stored.**

```sql
select id, tenant_id, label, extension_version,
       registered_at, last_seen_at, paused, revoked_at,
       secret is not null as has_secret
from agent_devices
order by registered_at desc
limit 5;
```

The newest row is yours: `tenant_id = 'acme'`, `label` like
`Macintosh · Chrome`, `paused = false`, `revoked_at` null.

The secret is stored in plain text (`agent_devices.secret`,
`String(64)`), and `proves_itself` compares the presented header against it in
constant time — so this is a direct comparison, not a hash check:

```sql
select id, secret from agent_devices where id = ':device';
```

That string must equal `chrome.storage.local["sro.deviceSecret"]`. It is what
`call()` sends as `X-Device-Secret` on **every** request
(`api.js:28-42`), and it is the half of the pair that steps 6, 7 and 9 all
depend on.

Register is idempotent and hands back the same secret, so pressing Save twice
is not a way to break this.

## 4. The socket

`channel.js` builds its target at `:295` from `state.apiUrl()`:

```
ws://localhost:8000/v1/agents/{device_id}/commands
```

with the subprotocol `["bearer", token, secret]` — three parts, because a
browser cannot set a header on a WebSocket, so the device secret rides beside
the credential.

**Check: the options page says the channel is open.** The **Command channel**
row reads `open`. If it does not, the reason is not hidden — `channel.js`
computes it inside `dial()` and the page prints it: *"this browser has no
credential"*, *"this browser is not registered yet"*, *"this browser has no
device secret — the next heartbeat fetches one"*, *"an administrator switched
this browser off"*.

**Check: the backend agrees.** Its log carries one line per attach, from
`agent_channel.py:65`:

```
INFO  device dev_… connected
```

And the store shows the browser is being heard from:

```sql
select id, last_seen_at, now() - last_seen_at as ago, paused, revoked_at
from agent_devices
where id = ':device';
```

`ago` should be under a minute or two — the heartbeat runs on the alarm that
wakes the worker.

A socket that closes immediately with 1008 is `read_device` refusing: the
credential is for another tenant, or the secret does not match the row you read
in step 3. The socket closes identically for absent, wrong and somebody else's,
deliberately — so debug it from step 3's comparison, not from the close code.

## 5. Demonstrate a job

Sign into the WMS in the same Chrome and do a job by hand, end to end — the one
you want offered back to you in step 7. Uploads batch on a timer, so give it a
minute.

**Check: batches arrive, and gestures are cut from them.**

```sql
select count(*) as batches, max(received_at) as newest
from observation_batches
where device_id = ':device';
```

```sql
select b.id, b.received_at, b.event_count, b.byte_count, count(g.id) as gestures
from observation_batches b
left join gestures g on g.batch_id = b.id
where b.device_id = ':device'
group by b.id, b.received_at, b.event_count, b.byte_count
order by b.received_at desc
limit 10;
```

Both `batches` and the newest row's `gestures` must grow while you work. Not
every batch yields gestures — a batch of page events with no interaction cuts
zero, and that is normal.

```sql
select g.id, g.at, g.system, g.url, g.gesture->>'kind' as kind
from gestures g
join observation_batches b on b.id = g.batch_id
where b.device_id = ':device'
order by g.at desc
limit 15;
```

`system` must be the real WMS host, and `kind` mostly `click`.

This is the one leg of the walkthrough that has been travelled before — 397
batches and 507 gestures were in the store on 2026-09-10, from a real Blue
Yonder host. It is here because it is the input to everything after it, not
because it is in doubt.

## 6. Shapes are served

`shapesFor()` (`service-worker.js:278`) asks on the gesture path, behind a
five-minute cache, and `api.shapes` sends the device id in the query while
`call()` puts the secret in the headers.

**Check: both halves together, and half a pair is a 404.** With the values from
step 3:

```bash
TOKEN=…            # step 2's token
DEVICE=dev_…       # step 3's id
SECRET=…           # step 3's secret

# Both halves — 200 and a list.
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" -H "X-Device-Secret: $SECRET" \
  "http://localhost:8000/v1/shapes?device_id=$DEVICE"

# The query without the header — 404.
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/shapes?device_id=$DEVICE"

# The header without the query — 404.
curl -s -o /dev/null -w '%{http_code}\n' \
  -H "Authorization: Bearer $TOKEN" -H "X-Device-Secret: $SECRET" \
  "http://localhost:8000/v1/shapes"
```

`200`, `404`, `404`. That is `asking_device`
(`backend/src/sro/interface/http/asking.py`) doing what its docstring promises:
*"Half a pair is a refusal, never a downgrade"* — because answering a named
device with no secret as "the tenant, then" would make `?device_id=` an
impersonation parameter.

The 404 matters more than it reads. `api.shapes` catches everything and returns
`[]`, deliberately, because this is the hot gesture path and a backend that is
down must cost the operator nothing. So a browser that sends half a pair gets
`[]` — an extension that has **silently stopped recognising anything**, with
nothing anywhere going red.

**Check: the list has the job you just demonstrated in it.**

```sql
select id, title, jsonb_array_length(coalesce(parameters, '[]'::jsonb)) as values
from workflows
order by title;
```

If the job is not here, step 7 cannot happen and the problem is mining, not the
extension.

## 7. The offer

Start the same job again in the WMS. Two gestures in, the tail matches a shape
and the panel offers to finish it. Then answer it — press **Yes** at step 8, or
dismiss it, or just do the job yourself. **Every** ending is reported, not only
the ones that become runs.

**Check: `offers` gets its first row ever.**

```sql
select id, seq, workflow_id, device_id, k, fate, run_id, at
from offers
order by at desc
limit 10;
```

`device_id` must be your browser. That value does not come off the body — the
extension sends it as `?device_id=` and `record_offer`
(`offers.py:54`) reads it from `asking`, refusing a request that names no
browser with a 403 and writing nothing. `RecordOfferRequest` has no `device_id`
field at all. This was the hidden half of phase 5's "same path" repoint: base
and headers alone would have left every fate refused.

`fate` is one of `accepted`, `dismissed`, `did_it`, `expired`, `diverged`
(`domain/skill/offers.py:44`).

```sql
select fate, count(*) from offers group by fate order by count(*) desc;
```

**On `reportOffer` returning whether the fate landed.** `api.reportOffer`
(`api.js:238`) now checks the status and answers `true` or `false` instead of
discarding the result — but **its only production caller throws that answer
away**: `service-worker.js:414` is `void api.reportOffer({…})`. So the returned
boolean reaches nobody, and the `offers` row above is the only proof a fate
landed. Do not look for a lost-fate counter in the panel; there is none.

## 8. Press yes

Press **Yes** on the offer. This is the step most likely to expose a defect.

**Check: `workflow_runs` gets its first row ever.**

```sql
select id, tenant_id, workflow_id, device_id, outcome, from_step,
       live, allow_focus, started_by, started_at, finished_at
from workflow_runs
order by started_at desc
limit 5;
```

`outcome = 'running'`, `live = true`, `device_id` your browser, `started_by`
read off the credential and not off the body — the press deliberately sends no
`started_by`, because a request that says who authorised it is a signature
nobody checked.

```sql
select count(*) as runs_with_no_device
from workflow_runs
where device_id is null or device_id = '';
```

Must be `0`.

**Check — and this is the one that matters — that the panel can poll the run.**
The `workflow_runs` row existing does **not** prove it. The defect this step
exists to expose is on the browser's side of the wire:

`POST /v1/workflow-runs` answers **201 with the whole row, keyed `id`**, where
the rig answered 202 and `{"run_id": …}`. The press in `service-worker.js`'s
`start-rig-run` read `started.run_id`, and now reads `started.id` (at `:1127`
today, and every line cite in this phase has drifted at least once — find it by
name). Read the old way it is `undefined`, `state.setActiveRun` records
`runId: undefined`, and `pollRigRun()` — which reads nothing but that record —
can never ask about the run. The row would still be in the table. The run would
still happen in the warehouse. The panel would show nothing, and **Approve could
never be reached.**

So the proof is in the browser, in the service worker's console:

```js
chrome.storage.local.get("sro.activeRun").then(h => console.log(h["sro.activeRun"]));
```

`{ runId: "run_…", at: …, source: "rig" }` — and `runId` must equal the `id` you
just read out of `workflow_runs`. **If it is `undefined`, the fix is not in the
build you loaded.**

**Check: the panel draws the run.** Steps appear a row at a time, one per
second (`K_RUN_POLL_MS = 1000`), from `GET /v1/workflow-runs/{id}`.

```sql
select run_id, ord, verdict, verdict_by, says, matched_by, stale,
       cost_usd, unpriced, sent is not null as has_sent
from workflow_run_steps
where run_id = (select id from workflow_runs order by started_at desc limit 1)
order by ord;
```

The rows here and the rows on screen must be the same rows.

**`chats` is the wrong table and this file was wrong to name it.** Nothing in a
workflow run writes it: `chats` is written only by `application/chat/understand.py`,
which is the reading path behind `POST /v1/chat`, and it will still be empty
when every check on this page has passed. It holds two rows as of 2026-09-12,
and both were put there by the chat door rather than by anything here — see
the count at the top of this file. A run's planning calls are rows in
**`model_calls`**, and the run's own totals are on the run and its steps
(`in_tokens`, `out_tokens`, `thought_tokens`, `cost_usd`, `unpriced`). Three dry
runs on 2026-09-11 put 7 rows in `model_calls` and none in `chats`. The query
below is kept because it is still the right query for the chat path — it is just
not evidence of anything on this page.

```sql
select id, workflow_id, in_tokens, out_tokens, thought_tokens,
       cost_usd, unpriced, error, at
from chats
order by at desc
limit 10;
```

## 9. Approve the parked write

The run reaches a step that would write, and stops. The panel shows what would
go out and offers **Approve**. Press it.

**It will park.** A step waits for a person when
`live && may_write && not earned(workflow)`, and `earned` needs
`K_EARNED_RUNS = 3` live held runs whose writes were verified by state
(`domain/execution/belts.py:179`). `workflow_runs` is empty, so no workflow has
earned anything, so **the first live run parks by construction.** After three
proven runs of the same job it stops asking — which is correct, and is why this
check gets harder to repeat later, not easier.

You have **five minutes** (`K_APPROVAL_WAIT_S = 300.0`). After that the step
fails with *"nobody approved the write within 5 minutes"* and the run is over.

**Check: `approvals` gets its first row ever, and `device_id` is not NULL.**

```sql
select run_id, ord, at, device_id
from approvals
order by at desc
limit 10;
```

```sql
select count(*) as approvals_by_nobody from approvals where device_id is null;
```

**`approvals_by_nobody` must be `0`.** A NULL approver is the exact failure
phase 5 fixed, and it does not announce itself — see below.

**Check: the approver is the browser that was driving.**

```sql
select a.run_id, a.ord, a.at,
       a.device_id  as approved_by,
       r.device_id  as driving_device,
       a.device_id is not distinct from r.device_id as approver_is_the_driver
from approvals a
join workflow_runs r on r.id = a.run_id
order by a.at desc
limit 10;
```

`approver_is_the_driver` must be `true`.

## 10. The run finishes

**Check: the outcome and the steps.**

```sql
select r.id, r.outcome, r.started_at, r.finished_at,
       r.finished_at - r.started_at as took,
       r.cost_usd, r.unpriced, r.in_tokens, r.out_tokens,
       jsonb_array_length(coalesce(r.withheld, '[]'::jsonb)) as withheld,
       (select count(*) from workflow_run_steps s where s.run_id = r.id) as steps
from workflow_runs r
order by r.started_at desc
limit 5;
```

`outcome` is one of `running`, `held`, `stopped`, `refused`, `aborted`,
`failed` (`domain/execution/workflow_run.py:15`). **`held` is the success**:
every step held. `finished_at` is set, and `withheld` should be `0` on a live
run — withholding is what a *dry* run does, and this one was `live = true`.

```sql
select run_id, ord, verdict, verdict_by, reason, matched_by, stale,
       cost_usd, unpriced
from workflow_run_steps
where run_id = ':run'
order by ord;
```

Verdicts are `held`, `failed`, `unclear`, `withheld`, `refused`, `skipped`,
`awaiting`, `done_by_operator`. The step you approved should now read `held`,
not `awaiting` — `awaiting` is *"shown to a person and waiting on their word"*,
and a step still saying it after the run ended means the tap never released the
wait.

`unpriced = true` on a step is a call whose cost could not be established — not
a free one. The row says so rather than drawing a zero, and the panel repeats
the distinction.

And the counts that were all zero at the top of this file:

```sql
select 'workflow_runs' as t, count(*) from workflow_runs
union all select 'workflow_run_steps', count(*) from workflow_run_steps
union all select 'approvals',          count(*) from approvals
union all select 'offers',             count(*) from offers
union all select 'chats',              count(*) from chats;
```

Every one of them non-zero is the acceptance criterion met.

---

## What would go wrong, and what it would look like

Three calls were fixed that would have broken at the switchover. Each was proven
against a fake `fetch` and none against a live backend. Here is how to recognise
a failure instead of assuming you mis-clicked.

### `rigApprove` — a 200 with `approved_by = NULL` looks like success

**This is the one to watch.** The old `rigApprove` hand-rolled its own `fetch`
with `rigHeaders()` and put `device_id` in a body. It therefore sent **neither**
`?device_id=` **nor** `X-Device-Secret`.

That is not a refusal. `asking_device` sees no device named and no secret and
returns `None` — *"the tenant, then"*, which is a legitimate caller, because a
supervisor's console holds the tenant's credential and has no extension of its
own. So the route:

- answered **200**,
- recorded the approval with **`approved_by = None`**,
- and **skipped the driving-browser check entirely**, because
  `NotDrivingThisRun` can only bind a caller that names a browser.

A live warehouse write, authorised by nobody, on the door whose entire job is
recording who authorised it. Nothing goes red. The panel says approved. The run
continues and writes.

**Symptom if the fix is wrong:** everything looks perfect and
`select count(*) from approvals where device_id is null` returns `1`. There is
no other sign. Run that query. It is the whole check.

If instead you see a **404** on the approve — that is the *good* failure. It
means one half of the pair is being sent and `asking_device` refused it, which
is what it is supposed to do. Compare the stored secret from step 3 against
`chrome.storage.local["sro.deviceSecret"]`.

A **403** means the browser proved itself and is approving a run it is not
driving — `NotDrivingThisRun`. Check step 8's `sro.activeRun` against the run
you are approving.

### `id` vs `run_id` — a run that happens where nobody can see it

`POST /v1/workflow-runs` answers `id`; the rig answered `run_id`.

**Symptom if the fix is wrong:** the press appears to work. The offer card
disappears. A row lands in `workflow_runs` with `outcome = 'running'`, and the
run drives the browser for real. But the panel shows **no run card, no steps,
and no Approve** — and `sro.activeRun` reads `{ runId: undefined, … }`. Because
Approve can never be reached, the run then parks on a person who has no button,
waits out the full five minutes, and dies with *"nobody approved the write
within 5 minutes"* — five minutes after a press that looked fine.

This is why step 8's check is the storage read and not the SQL. The SQL passes
either way.

### `reportOffer`'s `device_id` — every fate refused, silently

The path did not change; the *shape* did. `device_id` moved from the body to
the query, and `record_offer` 403s a request that names no browser and writes
nothing. `RecordOfferRequest` has no `device_id` field, so pydantic would have
ignored a body one without a 422.

**Symptom if the fix is wrong:** `offers` stays empty forever while everything
else works. Runs start, writes get approved, the panel behaves — and the one
measurement that says whether recognising a job early was worth doing records
nothing at all. `api.reportOffer` catches every failure and answers `false`, and
`service-worker.js:414` discards that answer with `void`, so there is no console
error and no counter. **An empty `offers` table after a session with offers in
it is the only symptom there is.**

### While you are there — three older traps

- **Two API workers.** Approve lands in a process where no `asyncio.Event` is
  waiting. Symptom: a 200 (or a 409 *"nothing is awaiting"*) and a run that
  still times out at five minutes. One worker.
- **A second panel window.** `approve-rig-run` refuses any run but the one
  `state.activeRun()` names: *"that run is not the one this browser is driving"*.
  That refusal is correct — it stops a stale card authorising a live write.
- **`chrome.storage` is per browser profile.** A device secret from another
  profile is a 404 on every device-scoped call, which step 6 reads as `[]`, which
  looks like a tenant with nothing proved.

---

## What this walkthrough cannot prove

**It does not move the mining measurement, and that is the number that decides
whether any of this was worth building.** The spec's criterion is **8 of 8
workflows named as themselves and 10 of 11 values**. Read it yourself rather
than trusting a figure in a document — it has moved twice this week:

```sql
select count(*) as workflows,
       sum(jsonb_array_length(coalesce(parameters, '[]'::jsonb))) as values
from workflows;
```

```sql
select id, started_at, proposed, kept, learned_parameters,
       cost_usd, coverage, lopsided, error
from mining_passes
order by started_at;
```

On 2026-09-10 the store held **7 of 8 workflows**, and the parameter count moved
from 3 to 11 during a pass at 09:40 that same morning — the first pass ever to
write a non-zero `learned_parameters` (14), because the pass that learnt three
parameters before it ran before migration 0041 created the column. Whether those
11 parameters are the 10 of 11 *values* the criterion names is a separate
question, and a mining one. **Nothing in this walkthrough touches it.** Running
every step above and passing every check leaves both figures exactly where they
were.
**Measured 2026-09-11, and the criterion is the replay, not the row count.**
The spec makes `make offer-replay` the acceptance test for recognition at every
phase after 4 — *8 of 8 named as themselves, 10 of 11 values by the end*. Run it
per tenant (`scripts/dry_run.py --replay … --tenant <t>`, then
`offer-replay.mjs` on the file), because the script serves one tenant's shapes
at a time and a job can only be recognised among the shapes it is served beside:

```
acme  7 jobs  7 offered as themselves  0 as another job  0 never   values  6/11
new   2 jobs  2 offered as themselves  0 as another job  0 never   values  6/6
```

Nine of nine, nothing misnamed, nothing lost. Two of those nine were being lost
before the cross-system fix above, which is the measurement that found it.

The store's own counts are 9 workflows and 17 declared parameters, and they are
a worse number than they look: `Review Video Recordings for Teach Task` is the
console recording itself and `Search for Work Areas` is the SSO hop, neither of
which is a warehouse job anybody wants offered. Two more bake a parameter's
value into their title — `Create Customer Type DSS`, `Create Warehouse Equipment
Type DDD` — so a second demonstration with a different value joins a job named
after the first. Both are mining defects, both are still open, and **nothing in
this walkthrough touches either.**


**Nor does it prove:**

- **That Chrome delivers `onStartup` to an evicted worker.** Step 2 proves
  `dropRetired` is wired to both hooks and removes the right three keys. It
  cannot reproduce MV3 tearing a worker down mid-`await`, which is the failure
  the second hook exists for.
- **`upload.js`.** It has no test suite of its own — batch assembly,
  `stageShots` ordering, the 401 re-throw, the screenshot drop. Step 5 exercises
  the happy path and nothing else. Four mutations to the upload path survived
  until phase 5's task 3 wrote the first test for `api.observations`.
- ~~**Anything about a second system.** Every gesture in the store came from one
  WMS host.~~ **Untrue since 2026-09-10.** Tenant `new` holds two jobs mined from
  demonstrations that cross `mail.google.com` and the WMS — the operator reads
  the field values out of a mail, types them into the form, and goes back to the
  mail between fields. `Create Customer Type DSS` and `Create Warehouse Equipment
  Type DDD`, seven steps each, four learnt parameters on the second. The claim
  this architecture exists to test now has evidence behind it, and the first
  thing that evidence found was a defect no single-system corpus could ever have
  shown: `match` skipped a shape unless its *first* step's origin matched the
  gesture in hand, so a job was offerable only while the operator was still on
  the system it started on. Fixed; the replay figures are below.
- ~~**The console.** Phase 6. A workflow run currently has **no details action in
  the panel at all**.~~ **Done in phase 6.** The five pages exist, a mined job
  has its own page at `/jobs/{id}` with the evidence and the screenshots under
  every cited step, and the panel's link is back — routed by id space, so a
  workflow run goes to `/jobs/runs/{id}` and a skill run still goes to
  `/runs/{id}`.
- **`apiUrl` and `consoleUrl` are unvalidated.** `isRigUrl` was the extension's
  only scheme check on an operator-typed URL and it died with the rig field.
  `<input type="url">` accepts any *absolute* URL, `javascript:` and `file:`
  included, and `consoleUrl` reaches `chrome.tabs.create` and an iframe `src`.
  Low severity, self-inflicted, and phase 6's.

**What it does prove, and nothing else does:** that `?device_id=` plus
`X-Device-Secret` resolves a real registered device against real Postgres, on
all four of the doors that need it — and that the four tables that have never
held a row can hold one.
