"""Runtime configuration. One Settings object, read from the environment."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _git_head() -> str:
    """The commit the working tree is on, asked once at import of the settings.

    Only the fallback: ``SRO_REVISION`` wins when it is set, because a container
    ships without a .git directory and knows its own build. Anything that goes
    wrong here -- no git, not a checkout, a repository that answers slowly -- is
    answered with "unknown". A process that refuses to start because it could
    not name itself would be a worse failure than the one this exists to catch.
    """
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - git is on PATH or it is not
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


_DEFAULT_PORTS = {"http": "80", "https": "443", "ws": "80", "wss": "443"}
_LOOPBACK = ("127.0.0.1", "localhost", "[::1]")
"""The same machine under three names. `Settings.attach_hosts` says so too, and
`our_own_origins` reads the same set rather than a second copy of it."""


def _origins_of(url: str) -> set[tuple[str, str]]:
    """One configured url as the (host:port, path prefix) pairs it stands for."""
    parsed = urlsplit(url if "//" in url else f"//{url}")
    host = (parsed.hostname or "").lower()
    if not host:
        return set()
    # `hostname` lowercases and strips userinfo but also strips the brackets an
    # IPv6 literal needs, so they go back on before it is compared to a netloc
    # anybody wrote by hand.
    if ":" in host:
        host = f"[{host}]"
    host = host.rstrip(".")
    try:
        port = str(parsed.port) if parsed.port else ""
    except ValueError:
        # A port nobody can read makes the whole url unusable. Dropping just
        # the port would widen the rule instead of narrowing it: a mistyped
        # `localhost:8000.` would become bare `localhost` and refuse every
        # page on it, including the warehouse test server.
        return set()
    if port and port == _DEFAULT_PORTS.get(parsed.scheme.lower()):
        port = ""
    prefix = parsed.path.rstrip("/") or "/"
    hosts = _LOOPBACK if host in _LOOPBACK else (host,)
    return {(f"{one}:{port}" if port else one, prefix) for one in hosts}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="SRO_", env_nested_delimiter="__", extra="ignore"
    )

    environment: str = "local"
    debug: bool = False

    revision: str = Field(default_factory=_git_head)
    """The commit this process is running, resolved once at startup.

    Every process reports it -- the API on ``/health``, the worker in the
    identity it polls Temporal with -- so that `make status` can put them beside
    the working tree's HEAD. This exists because an API left running for two
    days served a rule that had been fixed an hour earlier, and every step of
    the diagnosis looked like a code bug. Nothing enforces a match: a rolling
    deploy is two revisions on purpose."""

    database_url: str = "postgresql+asyncpg://sro:sro@localhost:5432/sro"

    ui_debugger_url: str = ""
    """CDP endpoint of a browser the executor may drive for L2.

    Empty by default, and an empty value is not a degraded mode: a run that
    would have escalated records that there was no browser rather than
    pretending the step was impossible."""

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "sro"
    s3_secret_key: str = "sro-secret"  # noqa: S105 - local MinIO default, overridden by SRO_S3_SECRET_KEY
    s3_bucket: str = "sro-artifacts"
    s3_region: str = "us-east-1"

    cors_origins: tuple[str, ...] = ()
    """Browser origins allowed to call this API, beyond the local console.

    The Chrome extension's origin is ``chrome-extension://<id>``, which is not a
    host anybody can guess and is stable per build. Empty in a deployment means
    only same-origin callers, which is the right default for an API whose other
    client is a server-rendered console.
    """

    mcp_servers: str = ""
    """Connectors a skill step may be mapped onto, as
    ``name=url[#token]``, comma separated.

    Empty is not a degraded mode. A deployment with no connectors runs every
    skill the way it always did; what it cannot do is promote a mail step past
    assisted, and `why_not_autonomous` says so rather than leaving somebody
    waiting on a streak that cannot move.
    """

    steel_base_url: str = "http://localhost:3010"
    steel_cdp_url: str = "http://localhost:9223"
    """Chrome DevTools endpoint Steel publishes. Playwright connects over it."""
    browser_width: int = 1600
    browser_height: int = 1000
    """The teaching browser's viewport.

    Steel defaults to something small, and this WMS is a dense ExtJS grid: at
    the default the operator is reading a postage stamp, and the accessibility
    tree that gets captured is one of a layout nobody uses.
    """

    steel_session_timeout_seconds: int = 3600

    attach_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "[::1]")
    """Hosts a recording may attach to a browser on.

    Attaching hands this system a debugger URL taken from the request body and
    connects to it. Unbounded, that is a request forgery primitive with a
    scripting engine on the end: any address the backend can reach, including
    cloud metadata endpoints. The operator's own Chrome is on this machine, so
    loopback is the whole legitimate set; widen it only for a remote debugger
    somebody actually runs.
    """

    api_url: str = "http://localhost:8000"
    """Where this deployment's own API answers.

    Used by the worker, so a scheduled run bound to an operator's browser is
    asked for by the process holding that browser's channel -- the API rather
    than the worker. Wrong there means scheduled device runs fail with a message
    naming this setting.

    Also `our_own_hosts` below, which is a different kind of wrong: too NARROW
    there and the evidence plane records this system recording."""

    console_url: str = "http://localhost:3000"
    """Where this deployment's own console is served.

    Read for one purpose: `our_own_hosts`, so the operator's own console is
    never recorded as warehouse work. `cors_origins` cannot stand in for it --
    that list is browser origins allowed to CALL this API, and a console served
    same-origin or proxied through its own server is not in it. This deployment
    is exactly that shape: `cors_origins` holds only the extension, and the
    console at :3000 was being captured with nothing to name it.
    """

    def our_own_origins(self) -> frozenset[tuple[str, str]]:
        """This deployment itself, as (host:port, path prefix) pairs.

        Never observable, and no operator grant widens them -- `admit` refuses
        them ahead of the tenant's policy. The operator had the console open in
        a tab while demonstrating, and the extension captured both halves: the
        console page itself (7 gestures in the real store) and the console
        asking the API to finish a recording (12 requests, one of them a POST
        that a mined workflow then reported as the write its job performs).

        Four things this has to get right, and the first version got one:

        **Loopback aliases.** `127.0.0.1`, `localhost` and `[::1]` are the same
        machine, which `attach_hosts` above already says in as many words. A
        rule whose whole justification is "a default nobody sets is a default
        nobody has" cannot then depend on the operator having typed one of the
        three -- and Chrome records whichever they typed. So a loopback host
        contributes all three.

        **Default ports.** `https://sro.acme.com:443` and
        `https://sro.acme.com` are one origin, and an operator writing the
        former left every call to the latter unrefused.

        **Host and port, not netloc.** `urlsplit().netloc` carries userinfo and
        preserves a trailing dot, so `http://user:pass@localhost:8000/` and
        `http://localhost:8000./` both slipped past a netloc comparison. Port
        still matters -- an API on 8000 beside a console on 3000 is the
        ordinary shape, and matching the hostname alone would refuse
        `localhost` outright, taking the warehouse test server on :63319 with
        it.

        **The path.** A corporate deployment fronting this system and the WMS
        on one hostname with path routing is an ordinary shape, and refusing
        the whole host would make every warehouse page on it permanently
        unrecordable -- no grant able to restore it, and the refusal reason
        deliberately names no host, so nobody would know why. The prefix is
        carried so `https://apps.acme.com/sro` refuses `/sro/...` and nothing
        else. `/` is the usual answer and matches the whole origin.

        `cors_origins` is included as well: an origin trusted to call this API
        is part of this system by definition. It is not a substitute for
        `console_url` -- a console served same-origin or proxied through its
        own server never appears in it, which is exactly this deployment.
        """
        found: set[tuple[str, str]] = set()
        for url in (self.api_url, self.console_url, *self.cors_origins):
            found |= _origins_of(url)
        return frozenset(found)

    temporal_address: str = "localhost:7233"

    temporal_namespace: str = "default"

    otlp_endpoint: str | None = "http://localhost:4318"
    service_name: str = "sro-backend"

    inline_body_limit_bytes: int = Field(default=256 * 1024)
    """Payloads above this go to object storage and the row keeps the URI.
    Nothing is discarded either way -- see docs/11-capture-completeness.md."""

    observation_artifact_bytes: int = 8_000_000
    """Bytes one artifact upload may carry. The rig's `K_ARTIFACT_BYTES`
    (`new_agent_arch/src/rig/api.py:374`), with its measurement: a full-page PNG
    of a warehouse form is a few hundred kilobytes; eight megabytes is a retina
    screen of noise. Past this, the bytes are not a picture of anything the rig
    reads.

    The measurement travels with the number on purpose. A constant whose reason
    is missing is one the next person re-tunes by guess."""

    observation_batch_events: int = 5000
    """Events one `POST /v1/observations` may carry. The rig's `K_BATCH_EVENTS`
    (`new_agent_arch/src/rig/api.py:379`), with its measurement: the extension
    flushes about once a minute; the busiest measured minute was under a hundred
    gestures, and the whole 81-gesture measured day would fit sixty times over.
    Past this is not capture, it is a payload.

    A bound on one request and not on a day: a browser with more than this to
    say splits it, and the refusal names the count so that it can."""

    capture_drain_interval_seconds: float = 5.0
    capture_screenshot_per_frame: bool = True

    capture_video: bool = True
    """Screencast the demonstration. Encoded as it arrives, so a long session
    costs disk rather than memory."""

    capture_video_fps: int = 2
    """Frames per second for the session video.

    Sampled with screenshots rather than a screencast: a screencast would take
    the live view away from the operator (Chrome allows one consumer per page).
    """

    capture_redact_secret_values: bool = True
    """Remove credential values at the point of capture.

    The single exception to keeping everything. A password is not evidence of
    what happened; it is a key to the customer's system. Turning this off makes
    the evidence store a credential store -- do not, without a decision that says
    who is accountable for it.
    """

    vault_path: str = "./.sro-vault"
    vault_key: str | None = None
    """Fernet key for the file vault. Without it the vault refuses to start
    rather than writing plaintext. Generate one with `make vault-key`."""

    transcription_enabled: bool = False
    """Narration transcription is optional. Default binding is NullTranscriber."""

    mining_sweep_seconds: float = 900.0
    """How often a day's observation is mined for tasks worth automating.

    A loop rather than a schedule, for the same reason as the session keeper: it
    holds no state worth replaying and a missed sweep is corrected by the next
    one. Mining is idempotent -- an episode already recorded is not counted
    twice -- so the only cost of running it often is reading blobs."""

    mining_window_hours: int = 24
    """How far back each sweep looks. Wider than the interval on purpose:
    evidence uploaded late still gets mined, and re-reading what was already
    mined changes nothing."""

    session_sweep_seconds: float = 600.0
    """How often the keeper looks at the connected systems.

    Not how often it signs in -- that is decided per system from how long its
    sessions have been observed to last. This is only how often the question is
    asked, and asking is a cached read."""

    retention_sweep_seconds: float = 86400.0
    """How often expired evidence is deleted. Once a day by default: a
    retention window is measured in days, so checking more often than that
    buys nothing but repeated table scans."""

    auth_secret: str = ""
    """The key this deployment signs its own credentials with.

    Unset, every authenticated endpoint answers 503 rather than letting
    anything through: a system that cannot check who is asking must refuse, and
    a default here would be a key every deployment shares. Generate one with
    `make auth-secret`."""

    gemini_api_key: str = ""
    """Without it every model-backed adapter stays unbound and the system runs
    exactly as it does today -- deliberately, for deployments that may not send
    a customer's screen or a customer's words to a hosted model."""

    gemini_timeout_ms: int = 120_000
    """How long one model call may hang before it is abandoned.

    The SDK's own default is no timeout at all, which is not a timeout anyone
    chose -- it is the absence of one. Measured here, on a laptop whose VPN
    came up mid-run: the TCP connection stayed ESTABLISHED to a Google address
    while the request never completed, and a reading pass sat on that one call
    for **19 hours** without reading a single gesture or printing a line. A
    nightly `sro.cli.read_cron` would have done the same thing, silently, and
    the next night's run would have found the previous one still holding on.

    Two minutes, against a slowest measured call of ~11s on
    `gemini-3.1-pro-preview`: far enough above the real distribution that a
    slow-but-live call is never cut off, and short enough that a dead socket
    costs one gesture rather than a night. A call that trips this comes back
    through the asker's own `except` as an errored `Answer` -- billed or not,
    recorded either way -- which is what the rest of the rig already knows how
    to carry."""

    gemini_read_tail: int = 0
    """How many previous readings each gesture is read against.

    Zero. The tail was carried for one stated purpose -- deciding `continues`
    -- which nothing consumes: `mining_pass` does not contain the word and
    `window.as_evidence` leaves it out of what the miner is shown. That alone
    is not a reason to drop it, so it was measured: three passes of the real
    `sro.cli.read_cron` over the same 164 captured gestures, scored on the 95
    with hand-labelled ground truth.

    What the tail costs, per whole pass:

    | | tail=8 | tail=0 |
    |---|---|---|
    | prompt tokens | 172,898 | 143,831 |
    | output tokens | 112,709 | 79,491 |
    | cost | $0.5523 | $0.4060 |
    | readings answered from one already paid for | 0.0% | 17.1% |

    The cascade is the part that cannot exist alongside it: keyed on the
    evidence a gesture is ACTUALLY read against, which with a tail ends in the
    last eight readings, no two questions are ever the same.

    What the tail buys: **nothing measurable.** Typed value 100% either way,
    entity 100% either way, operator-typed fields 100% either way -- once the
    fold stopped depending on it, which is `with_recent_values`'s own story and
    the reason the first run of this experiment looked worse.

    **And the reason given here for hesitating was wrong, measured.** This
    docstring used to say dropping the tail "moved the wording of `act` and
    `object` on 76% of gestures", offered as the thing a customer would
    notice. It does move them -- on 85.3%. But two passes at the SAME setting
    move them on **74.7%**, so almost all of that is the model being
    non-deterministic and only about ten points of it is the tail. The same
    goes for the verb score (91.1%, 90.0%, 88.9% across three passes): two
    identical configurations disagree on the leading verb for 24 of 95
    gestures, which is wider than any gap between the arms. Wording churn is
    not a tail effect; it is the weather.

    Set it back to 8 to get the old behaviour exactly, `SRO_GEMINI_READ_TAIL=8`.
    A deployment that later finds something to do with `continues` should --
    that is the one field this pays for."""

    gemini_read_at_once: int = 8
    """How many gestures one reading pass asks about at the same time.

    Only reachable with `gemini_read_tail` at 0, and the loop enforces that by
    reading one at a time whenever a tail is configured: with one, each reading
    is an input to the next, so they cannot be in flight together by
    definition. Dropping the tail is what makes the question askable at all.

    Eight, and the ceiling is somebody else's quota rather than anything here.
    A burst that trips a rate limit measures the rate limit; a burst large
    enough to matter also puts that many calls on the bill before the day's cap
    can be looked at again, which is checked once per pass and not per gesture.

    Measured, the same 164 captured gestures read by the real
    `sro.cli.read_cron`: **148 seconds at eight, against 683 and 579 seconds
    for two serial passes of the identical work.** So a little under 4x, not
    the 8x the width suggests -- a group waits for its slowest member before
    the next goes out, and nothing here starts a ninth call while eight are in
    flight. Head-of-line blocking is the price of committing a group at a time,
    and committing a group at a time is what keeps a pass that dies from
    throwing away what it has already paid for.

    Note the spread in the two serial numbers -- 683s and 579s on identical
    work. Wall clock here is a shared API on somebody's network, so treat 4x as
    the shape and not the constant.

    Only the model calls go out together. The pictures are fetched before and
    the readings saved after, one at a time, because both of those go through
    the unit of work -- and a `AsyncSession` held by two coroutines at once is
    the kind of failure that passes every test and corrupts a connection in
    production."""

    daily_usd_cap: float = 5.0
    """What one day of model calls may cost before the rig stops asking:
    readings, mining passes, runs and the chat door, summed.

    The rig's `read_on_ingest` bills per gesture as capture arrives, so an
    unattended run spends whatever the operator's day produces. On the
    measured evidence that is about $0.37 per 81-gesture day, but the whole
    point of watching every tab is that a day is thousands, and nothing here
    knew what the ceiling was. A pass or a run is a bigger call than a
    reading, and the cap that saw only readings let a day of those through
    untouched. This backend's own reading door, `POST /v1/gestures/read`, is
    deliberately not that: pulled like `/v1/mine` rather than pushed on every
    ingest, so a batch upload never itself triggers a model call.

    A cap that stops asking is honest in a way a cap that stops CAPTURE is not:
    the evidence still arrives and is still stored, so raising this tomorrow
    reads what today declined. Over the cap the rig's `/v1/mine`, `/v1/chat`
    and `POST /v1/runs` answered 429 and said how much of what; phase 4 names
    the backend's own, and none of the three are here -- there is no
    `/v1/chat`, a run is `POST /v1/skills/{skill_id}/runs`, and
    `POST /v1/candidates/mine` DOES exist and is candidate mining, an
    unrelated thing that the first name greps straight into. Zero disables the
    asking entirely; a negative value means no cap, which is what a deliberate
    one-off measurement wants. A run already going finishes on its own budget."""

    gemini_transcription_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    gemini_vision_model: str = "gemini-3.7-flash"
    """Computer use is native here rather than a separate specialised model.
    Checked against the account rather than assumed: the standalone
    `gemini-2.5-computer-use-preview` still answers, and this one accepts the
    same tool while being the model everything else already uses."""

    gemini_intent_model: str = "gemini-3.7-flash"
    """Chat: reading one sentence, extracting values. An operator is waiting, so
    this is the fast one -- measured at ~2.3s against ~4.8s for the pro model,
    for a job where the answer is checked against the skills that exist anyway."""

    gemini_interpreter_model: str = "gemini-3.1-pro-preview"
    """Reading a demonstration into a workflow, once per induction. Nobody is
    watching the clock, being wrong is expensive and lasting, and the reading is
    what an operator will see for the life of the skill -- so this is the
    reasoning model. It cannot enable computer use, and does not need to."""

    gemini_mine_model: str = "gemini-3.1-pro-preview"
    """The model one mining pass asks. The rig's `mine_model`
    (`new_agent_arch/src/rig/config.py:20`), and the same string as
    `gemini_interpreter_model` above by coincidence rather than by design --
    they answer different questions and each is re-tunable without the other.

    This model at `K_EFFORT="high"` is what spent $2.00 over a day of real
    gestures and kept nothing. The run and all of its numbers are written down
    once, beside the effort knob that fixed it, at `domain/skill/umbrella.py:23`
    -- cited and not copied, because a measurement kept in two places is a
    measurement that drifts, and only one of the two would be corrected. This
    setting is the name; that constant is the reason it was affordable."""

    gemini_plan_model: str = "gemini-3.8-flash"
    """What plans each step of a workflow run. The rig's `plan_model`
    (`config.py:41`). Deliberately the fast model: a run plans once per step and
    a slow plan is felt by an operator standing at a screen."""

    gemini_rescue_model: str = "gemini-3.1-pro-preview"
    """What re-plans a step the plan model got wrong. The rig's `rescue_model`
    (`config.py:45`). The expensive model earns its price here and not above:
    it is asked once per failure, not once per step."""

    gemini_read_model: str = "gemini-3.8-flash"
    """What reads one gesture into an intent -- `sro.domain.observation.
    reading`, called once per gesture, hundreds a day. The rig's own
    `intent_model` (`new_agent_arch/src/rig/config.py:19`), renamed here
    because this deployment's `gemini_intent_model` above already names an
    unrelated door -- reading one sentence out of a chat message, not one
    gesture out of a browser.

    A real bake-off against gemini-3.1-flash-lite and gemini-3.1-pro-preview,
    on real captured gestures, measured this one paying $0.0024/gesture at
    ~4.1s against flash-lite's $0.0003/gesture at ~1.2s and pro-preview's
    $0.0140/gesture at ~11.5s -- and, checked against ground truth rather than
    against each other, this one and pro-preview read the real DOM identifiers
    correctly while flash-lite drifted onto the wrong screen entirely once its
    own wrong reading entered its tail. Pro-preview bought nothing over this
    one on the same evidence. Worth re-running once `with_recent_values` and
    the thin-gesture picture are live in production: both were missing when
    that bake-off ran."""

    interpretation_enabled: bool = False
    """Reading one demonstration as a workflow sends the captured calls and
    bodies to a hosted model. Same rule as every other egress: a key is not
    consent, so this is its own switch. Off, a single demonstration still
    becomes a skill -- with mechanical step descriptions and no proposed
    parameters."""

    vision_enabled: bool = False
    """Whether a screen may be sent to a hosted model at all.

    The setting that governs a customer's warehouse screens leaving the
    deployment, and it was the one with nothing written next to it -- the
    paragraph above belongs to the switch above it. Off, the rungs that replay
    what somebody demonstrated work exactly as they do now; what stops is the
    rung that looks at a screen nobody has demonstrated.

    Separate from the key, like every other egress here: a step whose control
    has vanished then fails with that reason rather than quietly reaching for a
    model. (That sentence spent some time stranded after
    `keycloak_client_secret`, documenting nothing -- a second orphan of the same
    move this docstring already records.)"""

    keycloak_realm_url: str = ""
    """The realm that issues offline tokens for the connected system.

    Empty means no token source: runs authenticate with the session cookies,
    which work and expire on the identity provider's schedule."""

    keycloak_client_id: str = ""

    keycloak_client_secret: str = ""
    """Only for a confidential client. Keycloak answers a public client sent a
    secret, and a confidential one sent none, with the same "Invalid client"
    -- so this is set when the realm says the client is confidential rather
    than guessed at."""
    knowledge_embeddings_enabled: bool = False
    """Embeddings order what a structured filter already chose. Off by default:
    retrieval works without them, and turning them on sends the knowledge base's
    titles to a hosted model."""


@lru_cache
def get_settings() -> Settings:
    return Settings()
