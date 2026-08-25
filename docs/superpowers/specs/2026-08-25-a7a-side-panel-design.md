# A7a — the extension side panel

The operator's surface, docked beside the system they are working in. This spec
covers the panel itself; two pieces brainstormed with it were split out and get
their own designs:

- **A7b** — triggers UI in the console. `GET/POST/PATCH /v1/triggers` have had no
  screen since they were built, which is also why `may_take_focus` — plumbed end
  to end in A5 — has no way to be turned on by a human.
- **A7c** — acting on a join suggestion. `docs/15` deliberately left it open, and
  the panel makes its absence visible by showing suggestions read-only.

Read [`docs/14-extension-protocol.md`](../../14-extension-protocol.md) §4 for the
endpoints, and [`docs/15-observation-to-tasks.md`](../../15-observation-to-tasks.md)
for what a candidate is and which parts of one a model wrote.

## Why a panel when a console exists

The console renders candidates, chat, runs, skills, recordings and knowledge
already. The panel is not a second console; it is the surface that knows **which
tab you are looking at**, and that difference is the whole justification:

- teaching is a control you want beside the page being taught, not on a settings
  screen that cannot be the tab you mean;
- a run performing in this browser has to be visible and stoppable *while it
  happens*, which a tab you navigated away from cannot do;
- "tasks you keep doing **here**" is a different question from "tasks you keep
  doing", and only one of them can be asked by a page that knows the host.

Everything else is the console, framed. One implementation of each review
screen, so nothing drifts.

## The split

**Native panel UI** — anything that needs `chrome.*` or the current tab:

| Control | Message to the worker | Notes |
|---|---|---|
| REC state and why not | `status` | already returns `capturing` / `because` |
| Command channel state | `status` | `open` / `connecting` / `closed` |
| Pause | `set-paused` | the operator's own pause, not the administrator's |
| Teaching start/stop | `teach-start` / `teach-stop` | **`teach-start` gains an optional `tabId`** |
| Run status and abort | `status`, **`abort-run`** | new: the worker records the run it is performing |
| Purge the last hour | `purge` | exists |
| Tasks you keep doing here | — | reads the API directly with the extension's token |

**Framed console** — everything else, in an `<iframe>` the panel can navigate to
`/console`, `/candidates`, `/runs/{id}`.

The options page keeps connect/disconnect/exclusions and **loses teaching
start/stop to the panel**. It gains one setting: the **console URL**, which is a
different origin from the backend and cannot be derived from it.

## Manifest

```jsonc
"permissions": [..., "sidePanel"],
"side_panel": { "default_path": "src/panel/panel.html" },
"key": "<public key>"          // so the extension id is stable
```

`chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })` in the
worker's install handler, so clicking the toolbar action opens the panel. Chrome
114+; the manifest already floors at 116.

The `key` is not decoration. The console's allowlist (below) names an extension
origin, and an unpacked extension's id changes on every load without one.

## The credential handoff

The console keeps its credential in `localStorage`, and Chrome partitions
storage for framed third-party contexts — so a console framed in the panel
cannot see the token from its own tab. It has to be handed across.

1. The panel frames the console and, on load, posts
   `{kind: "sro.credential", token}` with `targetOrigin` set to **the configured
   console origin**. Never `"*"`: a wildcard hands the credential to whatever
   the frame has navigated to.
2. The console accepts only when **both** hold: `event.origin` is in
   `NEXT_PUBLIC_EXTENSION_ORIGINS`, and `window.top !== window.self`. A console
   open in an ordinary tab must never take a token from a message — that turns
   any page that can reach it into a credential injector.
3. Unset allowlist means **accept nothing**. A deployment that does not want the
   panel gets that for free.
4. The console replies `{kind: "sro.credential.ok"}`. The panel shows a refused
   handshake as a refusal — a cross-origin frame will not tell us it failed to
   load, so the reply is the health check.
5. The token never appears in a URL, for the reason `docs/14` already gives for
   the WebSocket: a token in a URL is a token in every access log.

**Hardening that stands on its own:** the console sends no framing header today,
so any site can frame it. A7a adds
`Content-Security-Policy: frame-ancestors 'self' <extension origins>`.

With no credential held, the panel does not frame the console at all.

## The run the worker is performing

`commands.js` knows which tab it is driving and not which run. Every command
envelope carries `run_id`; it is currently read only by `abort`.

The worker records `{runId, since}` when a command carrying one arrives and
clears it after the settle window, so `status` can say what is happening and the
panel can offer **abort**. Abort adds the run to the same set the server's
`abort` command uses: every later command for that run answers `aborted`, which
`drivers.py` sorts as "there was no browser to act in" rather than a skill that
has drifted. The step already inside the page finishes — nothing can recall it —
so the control says "stop this run", which is what it does.

## Tasks you keep doing here

`GET /v1/candidates` with the extension's own token, so the list is that
operator's own. **The endpoint gains a `host` query parameter**: filtering
client-side after `limit=20` lets a task on the host you are looking at be
pushed off the list by twenty from elsewhere, which breaks the one thing the
panel exists to do.

Each row shows what the candidate is made of — times seen, minutes so far — and
whether its name is a model's sentence (`named_by_model`). Join suggestions are
shown **read-only**; acting on one is A7c.

Two actions:

- **Dismiss** — `POST /v1/candidates/{id}/dismiss` with a reason. Kept, not
  deleted, so it is not offered again next week as if it were new.
- **Teach** — `POST /v1/candidates/{id}/teach`. When it answers
  `needs_demonstration: true`, the panel offers **"show me once"**, which starts
  the teaching tier on this tab. That is the loop the console structurally
  cannot close.

What that produces is a **second recording**, not an append: the candidate's
recording was sealed when it was taught. The two pair through induction on their
derived objective key — what `teach.py` means by keeping the thin recording
because "the deliberate repetition this asks for will be diffed against it". If
the keys do not match they do not pair, and the panel says so rather than
leaving the operator believing they taught something.

## How it fails

| Situation | What the operator sees |
|---|---|
| No credential | "connect in options"; no frame, no API calls |
| No console URL | the native half works; the frame area says why it is empty |
| Handshake refused | named as a refusal, with the likely cause — the allowlist |
| Backend unreachable | the list says so; the strip already surfaces `lastError` |
| Not registered, paused, or paused by an administrator | which one, and teaching disabled rather than failing on click |
| Teaching already running elsewhere | which tab it was, since `teaching.start` stops the previous one |

Refresh is a `status` poll every 2s while the panel is visible, plus an immediate
one after any action. A worker→panel broadcast is tidier and has lifecycle edge
cases; marked `ponytail:` with the upgrade path.

## Testing

- **Real Chrome, existing browser harness.** The stub serves a fake console page
  at its own origin that echoes what it received: the handshake is tested end to
  end, including the panel reporting ok.
- **Two refusal tests, on the console's real handler in vitest:** a message from
  a non-allowlisted origin is ignored, and a top-level console ignores the
  message entirely.
- **`teach-start` with an explicit `tabId`** teaches that exact tab, not the
  heuristic's guess.
- **Abort:** a command carrying `run_id`, aborted from the panel, and the next
  command for that run answers `aborted`.
- **Contextual filter:** candidates on two hosts, one shown.
- **CSP:** the console's config emits `frame-ancestors` naming the configured
  extension origins.

Every test above is asserted against behaviour, not structure: the panel is
mostly composition, and a test that a button exists is a test that fails when
somebody renames a class.

## What is deliberately not here

- **Acting on a join** (A7c) — needs a decision recorded on the candidate so the
  next sweep does not re-offer what somebody already answered.
- **Triggers** (A7b) — console work, and nothing is blocked on it today.
- **A worker→panel push** — polling first, upgrade if it is ever felt.
- **Panel chat** — the framed console's `/console` is chat, and a second chat
  implementation is exactly the drift this design avoids.
