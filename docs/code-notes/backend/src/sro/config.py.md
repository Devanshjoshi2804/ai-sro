# Notes for `backend/src/sro/config.py`

Comments and docstrings moved out of [`backend/src/sro/config.py`](../../../../../backend/src/sro/config.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../backend/src/sro/config.py#L1): Docstring

> Runtime configuration. One Settings object, read from the environment.

## module, [line 28](../../../../../backend/src/sro/config.py#L28): Note on the line above

Code: `_LOOPBACK = ("127.0.0.1", "localhost", "[::1]")`

> The same machine under three names. `Settings.attach_hosts` says so too, and
> `our_own_origins` reads the same set rather than a second copy of it.

## `_git_head`, [line 12](../../../../../backend/src/sro/config.py#L12): Docstring

> The commit the working tree is on, asked once at import of the settings.
>
> Only the fallback: ``SRO_REVISION`` wins when it is set, because a container
> ships without a .git directory and knows its own build. Anything that goes
> wrong here -- no git, not a checkout, a repository that answers slowly -- is
> answered with "unknown". A process that refuses to start because it could
> not name itself would be a worse failure than the one this exists to catch.

## `_origins_of`, [line 31](../../../../../backend/src/sro/config.py#L31): Docstring

> One configured url as the (host:port, path prefix) pairs it stands for.

## `Settings`, [line 58](../../../../../backend/src/sro/config.py#L58): Note on the line above

Code: `louder_for: str = ""`

> Tenants whose lines come through at DEBUG while the rest stay at INFO.
>
> Comma separated, and normally empty. A deployment asked to work out what
> happened to one customer had two choices and both were bad: turn the whole
> process to DEBUG -- every tenant, every sweep, every query, for as long as
> it takes to reproduce -- or see nothing. See `whose.Louder`.

## `Settings`, [line 60](../../../../../backend/src/sro/config.py#L60): Note on the line above

Code: `revision: str = Field(default_factory=_git_head)`

> The commit this process is running, resolved once at startup.
>
> Every process reports it -- the API on ``/health``, the worker in the
> identity it polls Temporal with -- so that `make status` can put them beside
> the working tree's HEAD. This exists because an API left running for two
> days served a rule that had been fixed an hour earlier, and every step of
> the diagnosis looked like a code bug. Nothing enforces a match: a rolling
> deploy is two revisions on purpose.

## `Settings`, [line 64](../../../../../backend/src/sro/config.py#L64): Note on the line above

Code: `ui_debugger_url: str = ""`

> CDP endpoint of a browser the executor may drive for L2.
>
> Empty by default, and an empty value is not a degraded mode: a run that
> would have escalated records that there was no browser rather than
> pretending the step was impossible.

## `Settings`, [line 71](../../../../../backend/src/sro/config.py#L71): Note on the line above

Code: `s3_public_endpoint_url: str | None = None`

> Where a *browser* reaches object storage, when that is not where this
> process reaches it.
>
> Deployed, the store sits on a private network as `minio:9000` and the
> operator's browser has never heard of that name -- so every presigned url
> the console draws a screenshot or a screencast from pointed at a host that
> does not resolve, and each one failed as a broken image rather than as an
> error anybody saw. Unset means the two are the same address, which is true
> on a laptop and was the only case ever exercised.

## `Settings`, [line 74](../../../../../backend/src/sro/config.py#L74): Note on the line above

Code: `cors_origins: tuple[str, ...] = ()`

> Browser origins allowed to call this API, beyond the local console.
>
> The Chrome extension's origin is ``chrome-extension://<id>``, which is not a
> host anybody can guess and is stable per build. Empty in a deployment means
> only same-origin callers, which is the right default for an API whose other
> client is a server-rendered console.

## `Settings`, [line 76](../../../../../backend/src/sro/config.py#L76): Note on the line above

Code: `mcp_servers: str = ""`

> Connectors a skill step may be mapped onto, as
> ``name=url[#token]``, comma separated.
>
> Empty is not a degraded mode. A deployment with no connectors runs every
> skill the way it always did; what it cannot do is promote a mail step past
> assisted, and `why_not_autonomous` says so rather than leaving somebody
> waiting on a streak that cannot move.

## `Settings`, [line 79](../../../../../backend/src/sro/config.py#L79): Note on the line above

Code: `steel_public_base_url: str | None = None`

> Where a *browser* reaches Steel, when that is not where this process
> reaches it.
>
> `live_view_url` is built by taking the path out of what Steel hands back
> and putting a base in front of it. That base was `steel_base_url`, which
> deployed is `http://steel:3000` -- a name on a private network, handed to
> an operator's browser as the live view of their own teaching session. It
> failed as a frame that never loaded. The same mistake as the presigned
> url in `s3_public_endpoint_url`, one service along, and found the same
> way: by asking what leaves the deployment.
>
> Unset means the two are the same address, which is true on a laptop.

## `Settings`, [line 89](../../../../../backend/src/sro/config.py#L89): Note on the line above

Code: `steel_tenants: tuple[str, ...] = ()`

> The spec's per-tenant `executor: extension | steel` (§9), as the list of
> tenants on Steel: `SRO_STEEL_TENANTS='["greyorange"]'`. Empty means every
> tenant stays on the extension, which is the rollout's step 1. The api and
> the worker share one environment block in the deploy file, so both read
> the same list.

## `Settings`, [line 81](../../../../../backend/src/sro/config.py#L81): Note on the line above

Code: `steel_cdp_url: str = "http://localhost:9223"`

> Chrome DevTools endpoint Steel publishes. Playwright connects over it.

## `Settings`, [line 83](../../../../../backend/src/sro/config.py#L83): Note on the line above

Code: `browser_height: int = 1000`

> The teaching browser's viewport.
>
> Steel defaults to something small, and this WMS is a dense ExtJS grid: at
> the default the operator is reading a postage stamp, and the accessibility
> tree that gets captured is one of a layout nobody uses.

## `Settings`, [line 102](../../../../../backend/src/sro/config.py#L102): Note on the line above

Code: `attach_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "[::1]")`

> Hosts a recording may attach to a browser on.
>
> Attaching hands this system a debugger URL taken from the request body and
> connects to it. Unbounded, that is a request forgery primitive with a
> scripting engine on the end: any address the backend can reach, including
> cloud metadata endpoints. The operator's own Chrome is on this machine, so
> loopback is the whole legitimate set; widen it only for a remote debugger
> somebody actually runs.

## `Settings`, [line 104](../../../../../backend/src/sro/config.py#L104): Note on the line above

Code: `api_url: str = "http://localhost:8000"`

> Where this deployment's own API answers.
>
> Used by the worker, so a scheduled run bound to an operator's browser is
> asked for by the process holding that browser's channel -- the API rather
> than the worker. Wrong there means scheduled device runs fail with a message
> naming this setting.
>
> Also `our_own_hosts` below, which is a different kind of wrong: too NARROW
> there and the evidence plane records this system recording.

## `Settings`, [line 106](../../../../../backend/src/sro/config.py#L106): Note on the line above

Code: `console_url: str = "http://localhost:3000"`

> Where this deployment's own console is served.
>
> Read for one purpose: `our_own_hosts`, so the operator's own console is
> never recorded as warehouse work. `cors_origins` cannot stand in for it --
> that list is browser origins allowed to CALL this API, and a console served
> same-origin or proxied through its own server is not in it. This deployment
> is exactly that shape: `cors_origins` holds only the extension, and the
> console at :3000 was being captured with nothing to name it.

## `Settings`, [line 126](../../../../../backend/src/sro/config.py#L126): Note on the line above

Code: `inline_body_limit_bytes: int = Field(default=256 * 1024)`

> Payloads above this go to object storage and the row keeps the URI.
> Nothing is discarded either way -- see docs/11-capture-completeness.md.

## `Settings`, [line 128](../../../../../backend/src/sro/config.py#L128): Note on the line above

Code: `observation_artifact_bytes: int = 8_000_000`

> Bytes one artifact upload may carry. The rig's `K_ARTIFACT_BYTES`
> (`new_agent_arch/src/rig/api.py:374`), with its measurement: a full-page PNG
> of a warehouse form is a few hundred kilobytes; eight megabytes is a retina
> screen of noise. Past this, the bytes are not a picture of anything the rig
> reads.
>
> The measurement travels with the number on purpose. A constant whose reason
> is missing is one the next person re-tunes by guess.

## `Settings`, [line 130](../../../../../backend/src/sro/config.py#L130): Note on the line above

Code: `observation_batch_events: int = 5000`

> Events one `POST /v1/observations` may carry. The rig's `K_BATCH_EVENTS`
> (`new_agent_arch/src/rig/api.py:379`), with its measurement: the extension
> flushes about once a minute; the busiest measured minute was under a hundred
> gestures, and the whole 81-gesture measured day would fit sixty times over.
> Past this is not capture, it is a payload.
>
> A bound on one request and not on a day: a browser with more than this to
> say splits it, and the refusal names the count so that it can.

## `Settings`, [line 135](../../../../../backend/src/sro/config.py#L135): Note on the line above

Code: `capture_video: bool = True`

> Screencast the demonstration. Encoded as it arrives, so a long session
> costs disk rather than memory.

## `Settings`, [line 137](../../../../../backend/src/sro/config.py#L137): Note on the line above

Code: `capture_video_fps: int = 2`

> Frames per second for the session video.
>
> Sampled with screenshots rather than a screencast: a screencast would take
> the live view away from the operator (Chrome allows one consumer per page).

## `Settings`, [line 139](../../../../../backend/src/sro/config.py#L139): Note on the line above

Code: `capture_redact_secret_values: bool = True`

> Remove credential values at the point of capture.
>
> The single exception to keeping everything. A password is not evidence of
> what happened; it is a key to the customer's system. Turning this off makes
> the evidence store a credential store -- do not, without a decision that says
> who is accountable for it.

## `Settings`, [line 141](../../../../../backend/src/sro/config.py#L141): Note on the line above

Code: `vault_project: str | None = None`

> The Google project whose Secret Manager holds this deployment's secrets.
>
> Set it and the vault is Secret Manager; leave it and the vault is the
> encrypted file beside this process. One switch and not two, so a deployment
> cannot be configured to believe it is using a cloud secret store while
> writing a file nobody backs up -- and a developer who points at a real
> project gets the real thing.
>
> The client is an optional install (`.[gcp]`). A project named without it
> refuses at first use with a sentence naming the extra, rather than
> `no module named google.cloud`.

## `Settings`, [line 144](../../../../../backend/src/sro/config.py#L144): Note on the line above

Code: `vault_key: str | None = None`

> Fernet key for the file vault. Without it the vault refuses to start
> rather than writing plaintext. Generate one with `make vault-key`.

## `Settings`, [line 146](../../../../../backend/src/sro/config.py#L146): Note on the line above

Code: `transcription_enabled: bool = False`

> Narration transcription is optional. Default binding is NullTranscriber.

## `Settings`, [line 148](../../../../../backend/src/sro/config.py#L148): Note on the line above

Code: `rig_sweep_seconds: float = 60.0`

> How often the RIG's miner reads each recorded tenant's day, or 0 to
> leave it to a deliberate call.
>
> This runs `mining_pass.mine`, whose output is a `workflows` row that `validate` has
> already refused nine ways, that no browser is offered until it is proven,
> and whose first run is always dry.
>
> On by default because a system whose whole promise is that it watches the
> work, notices the repetition and offers the job back cannot wait for
> somebody to press a button -- and until now `mine_pass` had exactly one
> caller and it was a door. Every mining result this project has measured
> came from a person running a script.
>
> A MINUTE, where this was an hour until an operator asked the obvious
> question: they did a task, nothing offered it back, and the reason was a
> clock with no idea their evidence had arrived. Measured on tenant `new`,
> an upload lands a median 27 seconds after the moment it covers, and then
> waited up to 59 more minutes for a sweep. Now: about three minutes, worst
> case, from doing a thing to being offered it.
>
> A minute does not cost sixty times an hour, because a pass that has nothing
> new to read is refused before it is paid for -- `_worth_a_pass` asks whether
> any evidence arrived since the last pass started, and a tenant nobody is
> working in is one cheap query per minute. What an interval this short DOES
> introduce is reading somebody mid-task, and `K_SETTLE_S` is the answer to
> that: a tenant still uploading is left alone until its evidence goes quiet.
>
> The interval also decides how much of a day gets read. A pass reads ONE
> window of the tenant's evidence, and the carry-over pool rotates which
> evidence that is: measured over ten simulated passes, pass 1 covered 81%
> and pass 2 96%, with nineteen gestures never shown. So passes are how
> coverage is bought, and more of them is more coverage as well as less
> waiting.
>
> What stops it costing more than that is `daily_usd_cap`, which `over_cap`
> measures PER TENANT -- so a busy tenant cannot spend a quiet one's budget,
> and the sweep's alphabetical order decides nothing. Measured over the 38
> passes stored across both real tenants: mean $0.46 and $0.27, worst case
> $2.00. A pass costs that only when there is something new to read, so the
> bill follows the work rather than the clock: a day with six bursts of
> activity is six passes, and the cap stops the pathological case -- somebody
> working continuously for eight hours -- at $100 rather than past it. A cap
> reached is logged per tenant and is not an error.
>
> A tenant whose browsers uploaded nothing in `mining_window_hours` is not
> swept at all. A pass re-reads that tenant's whole history, so one with no
> new evidence has nothing new to learn and would be paying to re-read a
> month nobody added to.
>
> A loop rather than a schedule, for the same reason as the session keeper:
> it holds no state worth replaying, and a missed sweep is corrected by the
> next one reading the same window.

## `Settings`, [line 150](../../../../../backend/src/sro/config.py#L150): Note on the line above

Code: `mining_window_hours: int = 24`

> How far back each sweep looks, for both miners. Wider than either
> interval on purpose: evidence uploaded late still gets mined, and
> re-reading what was already mined changes nothing.
>
> For the rig's sweep this bounds only WHICH TENANTS are mined -- a tenant
> whose browsers uploaded in the window. The pass itself then reads that
> tenant's whole history, which is `_one_pass`'s own recorded ceiling.

## `Settings`, [line 152](../../../../../backend/src/sro/config.py#L152): Note on the line above

Code: `session_sweep_seconds: float = 600.0`

> How often the keeper looks at the connected systems.
>
> Not how often it signs in -- that is decided per system from how long its
> sessions have been observed to last. This is only how often the question is
> asked, and asking is a cached read.

## `Settings`, [line 154](../../../../../backend/src/sro/config.py#L154): Note on the line above

Code: `retention_sweep_seconds: float = 86400.0`

> How often expired evidence is deleted. Once a day by default: a
> retention window is measured in days, so checking more often than that
> buys nothing but repeated table scans.

## `Settings`, [line 156](../../../../../backend/src/sro/config.py#L156): Note on the line above

Code: `auth_secret: str = ""`

> The key this deployment signs its own credentials with.
>
> Unset, every authenticated endpoint answers 503 rather than letting
> anything through: a system that cannot check who is asking must refuse, and
> a default here would be a key every deployment shares. Generate one with
> `make auth-secret`.

## `Settings`, [line 158](../../../../../backend/src/sro/config.py#L158): Note on the line above

Code: `gemini_api_key: str = ""`

> Without it every model-backed adapter stays unbound and the system runs
> exactly as it does today -- deliberately, for deployments that may not send
> a customer's screen or a customer's words to a hosted model.

## `Settings`, [line 160](../../../../../backend/src/sro/config.py#L160): Note on the line above

Code: `gemini_mine_timeout_ms: int = 600_000`

> How long a MINING pass's model call may hang before it is abandoned.
>
> Its own number, because `gemini_timeout_ms` below is not one call's
> timeout -- it is every call's, and the two ends of this system differ by
> four orders of magnitude. That one was chosen against "a slowest measured
> call of ~11s", which was one gesture being READ. A mining pass sends
> 162,000 tokens and answers in minutes.
>
> Measured on the deployed store, 2026-09-21: `gemini-3.1-pro-preview` took
> 107s, 135s and 217s over one corpus against a 120s limit, so it straddled
> the cutoff and **two of five passes died on a coin flip**. The
> deployment's own ledger carries 30 `ReadTimeout` rows, each recorded as $0
> and 0 tokens -- the worst shape a failure can have: the request was
> abandoned on this side rather than cancelled at Google, so it was very
> probably billed and is certainly not in the total.
>
> Ten minutes. Far past the slowest pass measured, and still short enough
> that a dead socket costs one sweep rather than a night -- which is what
> the paragraph below is about and why a timeout exists at all.

## `Settings`, [line 162](../../../../../backend/src/sro/config.py#L162): Note on the line above

Code: `gemini_timeout_ms: int = 120_000`

> How long one model call may hang before it is abandoned.
>
> The SDK's own default is no timeout at all, which is not a timeout anyone
> chose -- it is the absence of one. Measured here, on a laptop whose VPN
> came up mid-run: the TCP connection stayed ESTABLISHED to a Google address
> while the request never completed, and a reading pass sat on that one call
> for **19 hours** without reading a single gesture or printing a line. A
> nightly `sro.cli.read_cron` would have done the same thing, silently, and
> the next night's run would have found the previous one still holding on.
>
> Two minutes, against a slowest measured call of ~11s on
> `gemini-3.1-pro-preview`: far enough above the real distribution that a
> slow-but-live call is never cut off, and short enough that a dead socket
> costs one gesture rather than a night. A call that trips this comes back
> through the asker's own `except` as an errored `Answer` -- billed or not,
> recorded either way -- which is what the rest of the rig already knows how
> to carry.

## `Settings`, [line 164](../../../../../backend/src/sro/config.py#L164): Note on the line above

Code: `gemini_read_tail: int = 0`

> How many previous readings each gesture is read against.
>
> Zero. The tail was carried for one stated purpose -- deciding `continues`
> -- which nothing consumes: `mining_pass` does not contain the word and
> `window.as_evidence` leaves it out of what the miner is shown. That alone
> is not a reason to drop it, so it was measured: three passes of the real
> `sro.cli.read_cron` over the same 164 captured gestures, scored on the 95
> with hand-labelled ground truth.
>
> What the tail costs, per whole pass:
>
> | | tail=8 | tail=0 |
> |---|---|---|
> | prompt tokens | 172,898 | 143,831 |
> | output tokens | 112,709 | 79,491 |
> | cost | $0.5523 | $0.4060 |
> | readings answered from one already paid for | 0.0% | 17.1% |
>
> The cascade is the part that cannot exist alongside it: keyed on the
> evidence a gesture is ACTUALLY read against, which with a tail ends in the
> last eight readings, no two questions are ever the same.
>
> What the tail buys: **nothing measurable.** Typed value 100% either way,
> entity 100% either way, operator-typed fields 100% either way -- once the
> fold stopped depending on it, which is `with_recent_values`'s own story and
> the reason the first run of this experiment looked worse.
>
> **And the reason given here for hesitating was wrong, measured.** This
> docstring used to say dropping the tail "moved the wording of `act` and
> `object` on 76% of gestures", offered as the thing a customer would
> notice. It does move them -- on 85.3%. But two passes at the SAME setting
> move them on **74.7%**, so almost all of that is the model being
> non-deterministic and only about ten points of it is the tail. The same
> goes for the verb score (91.1%, 90.0%, 88.9% across three passes): two
> identical configurations disagree on the leading verb for 24 of 95
> gestures, which is wider than any gap between the arms. Wording churn is
> not a tail effect; it is the weather.
>
> Set it back to 8 to get the old behaviour exactly, `SRO_GEMINI_READ_TAIL=8`.
> A deployment that later finds something to do with `continues` should --
> that is the one field this pays for.

## `Settings`, [line 166](../../../../../backend/src/sro/config.py#L166): Note on the line above

Code: `gemini_read_at_once: int = 8`

> How many gestures one reading pass asks about at the same time.
>
> Only reachable with `gemini_read_tail` at 0, and the loop enforces that by
> reading one at a time whenever a tail is configured: with one, each reading
> is an input to the next, so they cannot be in flight together by
> definition. Dropping the tail is what makes the question askable at all.
>
> Eight, and the ceiling is somebody else's quota rather than anything here.
> A burst that trips a rate limit measures the rate limit; a burst large
> enough to matter also puts that many calls on the bill before the day's cap
> can be looked at again, which is checked once per pass and not per gesture.
>
> Measured, the same 164 captured gestures read by the real
> `sro.cli.read_cron`: **148 seconds at eight, against 683 and 579 seconds
> for two serial passes of the identical work.** So a little under 4x, not
> the 8x the width suggests -- a group waits for its slowest member before
> the next goes out, and nothing here starts a ninth call while eight are in
> flight. Head-of-line blocking is the price of committing a group at a time,
> and committing a group at a time is what keeps a pass that dies from
> throwing away what it has already paid for.
>
> Note the spread in the two serial numbers -- 683s and 579s on identical
> work. Wall clock here is a shared API on somebody's network, so treat 4x as
> the shape and not the constant.
>
> Only the model calls go out together. The pictures are fetched before and
> the readings saved after, one at a time, because both of those go through
> the unit of work -- and a `AsyncSession` held by two coroutines at once is
> the kind of failure that passes every test and corrupts a connection in
> production.

## `Settings`, [line 168](../../../../../backend/src/sro/config.py#L168): Note on the line above

Code: `daily_usd_cap: float = -1.0`

> What one day of model calls may cost before the rig stops asking:
> readings, mining passes, runs and the chat door, summed.
>
> The rig's `read_on_ingest` bills per gesture as capture arrives, so an
> unattended run spends whatever the operator's day produces. On the
> measured evidence that is about $0.37 per 81-gesture day, but the whole
> point of watching every tab is that a day is thousands, and nothing here
> knew what the ceiling was. A pass or a run is a bigger call than a
> reading, and the cap that saw only readings let a day of those through
> untouched. This backend's own reading door, `POST /v1/gestures/read`, is
> deliberately not that: pulled like `/v1/mine` rather than pushed on every
> ingest, so a batch upload never itself triggers a model call.
>
> A cap that stops asking is honest in a way a cap that stops CAPTURE is not:
> the evidence still arrives and is still stored, so raising this tomorrow
> reads what today declined. Over the cap the rig's `/v1/mine`, `/v1/chat`
> and `POST /v1/runs` answered 429 and said how much of what; phase 4 names
> the backend's own, and none of the three are here -- there is no
> `/v1/chat`, a run is `POST /v1/skills/{skill_id}/runs`, and
> `POST /v1/candidates/mine` DOES exist and is candidate mining, an
> unrelated thing that the first name greps straight into. Zero disables the
> asking entirely; a negative value means no cap. A run already going
> finishes on its own budget.
>
> **The default is no cap, by the owner's instruction (2026-09-16).** It was
> $5, and a day that reached it stopped every reading, every mining pass and
> every run for that tenant -- a warehouse whose jobs stop at four in the
> afternoon because a number in a config file ran out. The machinery is kept
> and works: a deployment that wants a ceiling sets one, and `over_cap` still
> says how much of what. What is gone is a ceiling nobody chose.

## `Settings`, [line 171](../../../../../backend/src/sro/config.py#L171): Note on the line above

Code: `gemini_embedding_model: str = "gemini-embedding-2"`

> The one model here that is not a chat model and cannot be one. Priced
> separately in `prices.py`; everything else on this list is `3.8-flash`.
>
> **Changing this makes every stored vector meaningless.** A distance between
> a vector from one model and a vector from another is noise, not a near
> miss, and `KnowledgeRow.embedding.cosine_distance` will happily order by it.
> So a change here is a change plus `make ingest-kb`, and the store is mixed
> until that finishes.
>
> The dimension deliberately does NOT move with it. `embedding.DIMENSIONS`
> stays 768 and `EmbedContentConfig(output_dimensionality=...)` asks for that
> size, which Matryoshka Representation Learning makes a real truncation of
> the larger vector rather than a different model. So the better embedding
> arrives with no migration on `knowledge_entries.embedding`, no rebuild of
> the HNSW index that only landed in 0050, and one re-embed.

## `Settings`, [line 173](../../../../../backend/src/sro/config.py#L173): Note on the line above

Code: `gemini_vision_model: str = "gemini-3.8-flash"`

> Computer use is native here rather than a separate specialised model.
> Checked against the account rather than assumed: the standalone
> `gemini-2.5-computer-use-preview` still answers, and this one accepts the
> same tool while being the model everything else already uses.

## `Settings`, [line 175](../../../../../backend/src/sro/config.py#L175): Note on the line above

Code: `gemini_intent_model: str = "gemini-3.8-flash"`

> Chat: reading one sentence, extracting values. An operator is waiting, so
> this is the fast one -- measured at ~2.3s against ~4.8s for the pro model,
> for a job where the answer is checked against the skills that exist anyway.

## `Settings`, [line 177](../../../../../backend/src/sro/config.py#L177): Note on the line above

Code: `gemini_interpreter_model: str = "gemini-3.1-pro-preview"`

> Reading a demonstration into a workflow, once per induction. Nobody is
> watching the clock, being wrong is expensive and lasting, and the reading is
> what an operator will see for the life of the skill -- so this is the
> reasoning model. It cannot enable computer use, and does not need to.

## `Settings`, [line 179](../../../../../backend/src/sro/config.py#L179): Note on the line above

Code: `gemini_mine_model: str = "gemini-3.8-flash"`

> The model one mining pass asks. The rig's `mine_model`
> (`new_agent_arch/src/rig/config.py:20`) was `gemini-3.1-pro-preview`, and
> this is the one of the three model names that is deliberately no longer
> the rig's.
>
> **Measured, 2026-09-21, against pro on identical copies of the deployed
> store** -- 904 gestures, the same 22 known workflows, the same
> `K_EFFORT="medium"`, the same window budget:
>
>     pro    8 passes, 2 of 5 finished inside the shipped timeout,
>            107s / 135s / 217s, mean $0.493, 3-10 proposals
>     flash  5 passes, 5 of 5 finished, ~115s, mean $0.235, 9-12 proposals
>
> and, on the number that decides it, **0 new jobs each**. Every proposal
> from both resolved as a job already stored or the same evidence read
> twice, because the store had converged.
>
> So this is not "flash mines better"; nothing here shows that, and a
> converged store cannot show it. It is the rule `gemini_rescue_model` below
> already states -- the expensive model earns its price where depth per call
> is the product -- applied to the call that is its opposite. A mining pass
> is 162,000 input tokens, one shallow judgement, and then the nine rules in
> `validate` that do the actual discrimination. The miner's job is recall;
> recall is the cheaper thing to buy, and `validate` is what refuses. Pro
> earns its price at the rescue rung, once per failure, and stays there.
>
> **And then it was re-run, on exactly that.** An operator demonstrated
> `Create a Transport Equipment Type` three times -- a screen this store had
> never held a job for -- and both models were given the same 159,929-token
> prompt over identical copies with that job rolled back:
>
>     flash  learned it,  10 proposed (1 new, 3 same_job, 6 same_occurrence),
>            nothing wrongly refused,   91s,  $0.2396
>     pro    learned it,   8 proposed (1 new, 2 same_job, 4 same_occurrence),
>            nothing wrongly refused,  338s,  $0.5032
>
> The same answer, 2.1x the price and 3.7x the wall clock. Flash gets there
> by thinking four times as hard -- 21,278 thought tokens against 4,821 --
> and still costs less, because thinking is billed at its own output rate.
> Note pro's 338 seconds: under the 120s that shipped before
> `gemini_mine_timeout_ms`, that pass would have died.
>
> So the choice is measured on novel evidence now and not only on a
> converged store. It is still n=1 on a job of this shape, on this
> application: a subtler one -- more steps, more interleaving, two systems --
> is the moment to run it again rather than assume, which costs $0.75 and
> ten minutes and has these numbers to beat.
>
> Both models at `K_EFFORT="high"` spend their whole output budget thinking
> and are truncated with nothing kept. The run and all of its numbers are at
> `domain/skill/umbrella.py:23` -- cited and not copied, because a
> measurement kept in two places is one that drifts.

## `Settings`, [line 181](../../../../../backend/src/sro/config.py#L181): Note on the line above

Code: `gemini_plan_model: str = "gemini-3.8-flash"`

> What plans each step of a workflow run.
>
> Three settings above were `gemini-3.7-flash` until 2026-09-15 -- the
> transcription, the vision rung and the chat door -- and `3.7-flash` is not
> in `prices.py`. So every call on those three recorded `cost_usd = 0.0` and
> the day's spend read lower than it was, which is the exact failure
> `prices.py` opens by describing. They are on the model the rest of the
> system already uses and the bakeoff already measured. The rig's `plan_model`
> (`config.py:41`). Deliberately the fast model: a run plans once per step and
> a slow plan is felt by an operator standing at a screen.

## `Settings`, [line 183](../../../../../backend/src/sro/config.py#L183): Note on the line above

Code: `gemini_rescue_model: str = "gemini-3.1-pro-preview"`

> What re-plans a step the plan model got wrong. The rig's `rescue_model`
> (`config.py:45`). The expensive model earns its price here and not above:
> it is asked once per failure, not once per step.

## `Settings`, [line 185](../../../../../backend/src/sro/config.py#L185): Note on the line above

Code: `gemini_read_model: str = "gemini-3.8-flash"`

> What reads one gesture into an intent -- `sro.domain.observation.
> reading`, called once per gesture, hundreds a day. The rig's own
> `intent_model` (`new_agent_arch/src/rig/config.py:19`), renamed here
> because this deployment's `gemini_intent_model` above already names an
> unrelated door -- reading one sentence out of a chat message, not one
> gesture out of a browser.
>
> A real bake-off against gemini-3.1-flash-lite and gemini-3.1-pro-preview,
> on real captured gestures, measured this one paying $0.0024/gesture at
> ~4.1s against flash-lite's $0.0003/gesture at ~1.2s and pro-preview's
> $0.0140/gesture at ~11.5s -- and, checked against ground truth rather than
> against each other, this one and pro-preview read the real DOM identifiers
> correctly while flash-lite drifted onto the wrong screen entirely once its
> own wrong reading entered its tail. Pro-preview bought nothing over this
> one on the same evidence. Worth re-running once `with_recent_values` and
> the thin-gesture picture are live in production: both were missing when
> that bake-off ran.

## `Settings`, [line 187](../../../../../backend/src/sro/config.py#L187): Note on the line above

Code: `interpretation_enabled: bool = False`

> Reading one demonstration as a workflow sends the captured calls and
> bodies to a hosted model. Same rule as every other egress: a key is not
> consent, so this is its own switch. Off, a single demonstration still
> becomes a skill -- with mechanical step descriptions and no proposed
> parameters.

## `Settings`, [line 189](../../../../../backend/src/sro/config.py#L189): Note on the line above

Code: `vision_enabled: bool = False`

> Whether a screen may be sent to a hosted model at all.
>
> The setting that governs a customer's warehouse screens leaving the
> deployment, and it was the one with nothing written next to it -- the
> paragraph above belongs to the switch above it. Off, the rungs that replay
> what somebody demonstrated work exactly as they do now; what stops is the
> rung that looks at a screen nobody has demonstrated.
>
> Separate from the key, like every other egress here: a step whose control
> has vanished then fails with that reason rather than quietly reaching for a
> model. (That sentence spent some time stranded after
> `keycloak_client_secret`, documenting nothing -- a second orphan of the same
> move this docstring already records.)

## `Settings`, [line 191](../../../../../backend/src/sro/config.py#L191): Note on the line above

Code: `keycloak_realm_url: str = ""`

> The realm that issues offline tokens for the connected system.
>
> Empty means no token source: runs authenticate with the session cookies,
> which work and expire on the identity provider's schedule.

## `Settings`, [line 195](../../../../../backend/src/sro/config.py#L195): Note on the line above

Code: `keycloak_client_secret: str = ""`

> Only for a confidential client. Keycloak answers a public client sent a
> secret, and a confidential one sent none, with the same "Invalid client"
> -- so this is set when the realm says the client is confidential rather
> than guessed at.

## `Settings`, [line 196](../../../../../backend/src/sro/config.py#L196): Note on the line above

Code: `knowledge_embeddings_enabled: bool = False`

> Embeddings order what a structured filter already chose. Off by default:
> retrieval works without them, and turning them on sends the knowledge base's
> titles to a hosted model.

## `Settings.our_own_origins`, [line 108](../../../../../backend/src/sro/config.py#L108): Docstring

> This deployment itself, as (host:port, path prefix) pairs.
>
> Never observable, and no operator grant widens them -- `admit` refuses
> them ahead of the tenant's policy. The operator had the console open in
> a tab while demonstrating, and the extension captured both halves: the
> console page itself (7 gestures in the real store) and the console
> asking the API to finish a recording (12 requests, one of them a POST
> that a mined workflow then reported as the write its job performs).
>
> Four things this has to get right, and the first version got one:
>
> **Loopback aliases.** `127.0.0.1`, `localhost` and `[::1]` are the same
> machine, which `attach_hosts` above already says in as many words. A
> rule whose whole justification is "a default nobody sets is a default
> nobody has" cannot then depend on the operator having typed one of the
> three -- and Chrome records whichever they typed. So a loopback host
> contributes all three.
>
> **Default ports.** `https://sro.acme.com:443` and
> `https://sro.acme.com` are one origin, and an operator writing the
> former left every call to the latter unrefused.
>
> **Host and port, not netloc.** `urlsplit().netloc` carries userinfo and
> preserves a trailing dot, so `http://user:pass@localhost:8000/` and
> `http://localhost:8000./` both slipped past a netloc comparison. Port
> still matters -- an API on 8000 beside a console on 3000 is the
> ordinary shape, and matching the hostname alone would refuse
> `localhost` outright, taking the warehouse test server on :63319 with
> it.
>
> **The path.** A corporate deployment fronting this system and the WMS
> on one hostname with path routing is an ordinary shape, and refusing
> the whole host would make every warehouse page on it permanently
> unrecordable -- no grant able to restore it, and the refusal reason
> deliberately names no host, so nobody would know why. The prefix is
> carried so `https://apps.acme.com/sro` refuses `/sro/...` and nothing
> else. `/` is the usual answer and matches the whole origin.
>
> `cors_origins` is included as well: an origin trusted to call this API
> is part of this system by definition. It is not a substitute for
> `console_url` -- a console served same-origin or proxied through its
> own server never appears in it, which is exactly this deployment.

## `_origins_of`, [line 36](../../../../../backend/src/sro/config.py#L36): Comment

Code: `if ":" in host:`

> `hostname` lowercases and strips userinfo but also strips the brackets an
> IPv6 literal needs, so they go back on before it is compared to a netloc
> anybody wrote by hand.

## `_origins_of`, [line 35](../../../../../backend/src/sro/config.py#L35): Comment

Code: `return set()`

> A port nobody can read makes the whole url unusable. Dropping just
> the port would widen the rule instead of narrowing it: a mistyped
> `localhost:8000.` would become bare `localhost` and refuse every
> page on it, including the warehouse test server.
