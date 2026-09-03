# The panel as a ledger — Design

**Status:** proposed · 2026-09-03
**Builds on:** `2026-09-02-the-panel-is-a-conversation-design.md` (one thread,
offers as messages, the press is the authorisation) and
`docs/design/extension-panel-brief.md` (states, constraints).
**Serves:** `2026-09-03-autonomous-workflows-design.md`, whose product surface
this is. Sub-plan 5 of that roadmap, pulled forward because the operator lives
here.
**Brand:** locked by `frontend/src/app/brand.css` and ADR 011. Nothing in this
document chooses a colour or a typeface.

## What is wrong today

Two screenshots taken on 2026-09-03 at 12:16 show it.

- The first thing on every tab, including claude.ai and localhost, is a
  "Not watching this tab" card with two buttons. A permission gate before
  anything useful, every time the operator switches tabs.
- The same panel says "you've done this 5 times, want me to do the next one?"
  and, further down, "nothing new noticed here". Two answers to one question,
  because one list is scoped to the host and the other is not.
- Four messages, all from the system, no buttons on any of them. The only
  affordance is a text box.
- Nothing says what is running, what ran today, what was confirmed, or what
  needs an answer. It is a log.
- "Ask for a task" appears twice: a button and the placeholder beside it.
- "Delete the last hour" and "Settings" sit in the footer, in the operator's
  eye line, where the composer should be alone.

## Decisions taken before design

The owner's, on 2026-09-03:

1. **The panel is the product's front door**, and it is a chat. The console is
   the supervisor's view.
2. **A mail that matches a task is said in the chat, as a card the operator
   can interact with**: read what was read from the mail, change a value,
   add one, say something to the run while it is going.
3. **Arriving on a page where a known task starts gets a prompt**: "you've done
   this here before, want me to do it?" Visible, highlighted, and short-lived.
   A prompt that stays is wrong.
4. **"Delete the last hour" and "Settings" leave the footer.** Both move under a
   profile menu in the strip at the top. The footer is the composer and nothing
   else.
5. **Panel first, console after.** The console gets the same thread component
   and its own spec.

## Design

### 1. Anatomy

Four bands. Only the ledger scrolls.

```
┌──────────────────────────────────────────┐
│ g AI-SRO                      Console ↗ ◐ │  strip: brand, console link, profile menu
│ ● bf56-kms…  watching 53 min           ▾  │  status chip; expands only to be pressed
├──────────────────────────────────────────┤
│ Today  3 done · 2 offers · 4 min saved    │  today line
├──────────────────────────────────────────┤
│ 12:04 ┃ Create a supplier                 │
│       ┃ done 5 times, about 161 s each    │
│       ┃ [ Do the next one ]  [ Not now ]  │  offer
│ 12:06 ┃ you  do it                        │  operator
│ 12:06 ┃ Running  Create a supplier        │
│       ┃ ✓ open the form                   │
│       ┃ ✓ fill 4 fields         [change]  │
│       ┃ ● save                confirming… │  run card
│ 12:07 ┃ Needs you  which address?         │
│       ┃ [A000144886] [A000221] [ type… ]  │  question
│ 12:08 ┃ Done  supplier 10233 created,     │
│       ┃ read back and matched   [Undo]    │  result
├──────────────────────────────────────────┤
│ [ Ask for a task, or describe it   ] Send │  composer, alone
└──────────────────────────────────────────┘
```

Alignment: everything left-aligned to one gutter after the time rail. No
centred text anywhere. Numbers, times, hosts, ids and call names in the mono
face; nothing else is.

### 2. The strip

**Brand and links.** Mark, name, "Console ↗", and a profile disc at the far
right. The disc opens a menu, anchored below it, not a page:

- Pause watching / Resume
- Delete the last hour
- Never watch this site
- Settings
- Disconnect this browser

"Delete the last hour" stays in the product because it is the operator's own
escape hatch, the one control that makes always-on observation defensible
(`docs/10-security-and-data.md`, ADR 008). It leaves the footer because an
escape hatch is not a thing pressed daily. Pressing it asks nothing and reports
what it did in the ledger: "deleted 14 minutes of evidence from this browser".

**The status chip.** One line under the brand. Dot, host, state, elapsed:

- `● bf56-kms…  watching 53 min`
- `● mail.google.com  watching 2 h`
- `○ claude.ai  not watched` (policy excludes it, or the operator did)
- `● bf56-kms…  recording a demonstration 1:12`
- `◐ bf56-kms…  paused`

The chevron expands the chip to the card that exists today, buttons and all.
The chip expands itself, without a press, in exactly four cases, because those
are the four where there is something to press: not connected; a grant that
has run out; the command channel closed while a run is expected; this host is
on the exclusion list and the operator is asking the panel to do something on
it. In every other state it is one line and stays one line.

**Not connected** is not a chip. It replaces the whole panel below the strip
with one card: what is true, and one button, "Connect". Nothing else is drawn,
because nothing else is true.

### 3. The today line

Three numbers, from evidence the system holds, nothing invented:

- **done**: runs that reached `SUCCEEDED` today for this operator.
- **offers**: offers in the thread today not yet answered.
- **saved**: the sum, over runs done today, of the candidate's observed
  `seconds_each`. That is the time the operator would have spent, measured
  from their own doings. Shown in minutes when over 90 s.

The line is hidden when all three are zero and the thread is empty, so a
first-day panel does not open with `0 · 0 · 0`.

### 4. The ledger

One thread, the operator's own, across every tab, as today. Rendered oldest
first with a time rail on the left: the hour and minute in mono, drawn once per
minute, not per message. A thin vertical line joins the entries so the day
reads as one continuous record.

Every message has a speaker (`operator`, `assistant`, `system`) as today, and
a `decision.kind` that decides its shape. Kinds the panel draws:

| kind | drawn as | buttons |
|---|---|---|
| `offer` | task name, count, seconds each | Do the next one · Not now |
| `mail_match` | task name, the mail's sender and subject, the values read from it, each editable | Run it · Not now |
| `nudge` | "you've done this here before" with the task name | Do it · Not for this page |
| `run` | the run card (§5) | Pause · Stop · Change |
| `question` | the sentence and its choices | one button per choice, plus a text field |
| `result` | what was made, whether it was read back, the undo line | Undo that · It's wrong |
| `failure` | what stopped it, in one sentence | one button, always: Try another way · Ask me · Open the page |
| `note` | a plain line | none |

A kind the panel has never heard of draws its text and nothing else, as today.
An answered offer, match or nudge keeps its words and loses its buttons, with
the answer as its own message underneath. No message is ever edited to show
its own outcome.

**What "offer" replaces.** The "Tasks you keep doing here" section is gone. A
task worth offering is an `offer` in the ledger. The candidate list itself
lives in the console.

### 5. The run card

The one place this design spends its boldness. A run is a message that keeps
changing while it is on screen, and the ledger is where it changes.

**Before it starts.** Every value the run will use is shown as a field, with
where it came from beside it in muted text: "read from the mail", "you said",
"same as last time". Every field is editable. A missing required value is a
field with nothing in it and the run does not start until it has something.
This is the Aug 27 decision, "ask everything before the run starts", drawn.

**While it runs.** One row per step. A glyph on the left says its state:

- `○` not yet
- `●` now, with a one-word verb after it: `sending`, `confirming`, `waiting`
- `✓` done and confirmed by a read-back
- `✓` in the warn colour: done, nothing read back to confirm it
- `✗` failed
- `⏸` waiting on the operator

A step that has not run yet shows `change` at the row's end. Pressing it turns
that step's values into fields. Changing one is recorded as an operator
message ("changed address to A000221") and the run continues with the new
value from that step on. A step already sent cannot be changed; the row says
so if pressed.

**Saying something to a run.** While a run is live, the composer's placeholder
changes to "Say something to this run". A sentence typed then is posted as an
operator message attached to the run (`decision: {kind: "note", run_id}`). The
run card shows it under the step it arrived during. Until the planner exists
(sub-plan 3), a note changes nothing and the card says "noted, I can't act on
this yet". When the planner exists, a note is what it reads before its next
step. Both behaviours are honest; neither pretends.

**Controls.** Pause stops before the next step and says so. Stop ends the run
after the step in flight, as today. Neither is a modal.

**After.** The card stops changing. A `result` message follows it, as its own
entry, with what was made, whether it was read back and matched, and the undo
line, exactly as `finished()` says today.

### 6. The mail match

A mail arrives in a watched tab and the watch recognises a task. Today this
is a card with "Run it" and "Not now". It becomes a `mail_match` message:

```
12:31 ┃ A mail matched  Create a supplier
      ┃ from  procurement@kenco.com
      ┃ re    New supplier: Acme Fasteners
      ┃ supplier name   Acme Fasteners        read from the mail
      ┃ address         [ pick… ]             nothing said this
      ┃ [ Run it ]  [ Not now ]
```

Each value is a field. The operator can change one, fill an empty one, or add
one the task knows about but the mail did not mention (a chevron reveals the
task's other parameters). Pressing "Run it" starts the run with the fields as
they stand, and the values that came from the mail and the ones the operator
typed are both recorded on the run, as they are today.

The match is written once, into the thread, and survives the panel closing.
Two mails that match the same task are two entries.

### 7. The nudge, and how long it lives

**When it fires.** The tab being watched lands on a page where a known task
starts, no run is live, and this page has not been nudged in this visit. "A
page where a task starts" is `starts_on` on the candidate: the host and path
of the first page event in its episodes, recorded at mining time and carried
to the skill at induction. Query strings are ignored. Only candidates that
have a skill, or are past `WORTH_OFFERING`, can nudge.

**How it looks.** A `nudge` entry at the bottom of the ledger with the accent
line on its left edge, the only entry that carries the accent. The panel
scrolls to it. If the panel is closed, a pill in the page's top-right corner,
in the page's shadow root beside the driving banner: "AI-SRO · do this one?"
Clicking the pill opens the panel. There is no toast, no sound, no modal.

**How long it lives.** Three ends, whichever comes first:

1. The operator answers it.
2. The operator does the task themselves. The first call that matches the
   task's own first call marks the nudge `did it by hand`; the entry loses its
   buttons and keeps one line. Nothing else is said.
3. The operator does something else. Ninety seconds after the nudge with no
   matching call, or navigation away from `starts_on`, the entry collapses
   to one muted line, "you were on Create a supplier", with no buttons.

Ninety seconds because the observed `seconds_each` for the tasks in the
screenshots is 36 s and 161 s; a nudge that outlives the task is a nudge that
was ignored. The number is a constant in one place and the entry shows its
own countdown only in the last fifteen seconds, as a thinning accent line,
not a clock.

**Never twice.** One nudge per page visit. "Not for this page" mutes that
`starts_on` for the rest of the day for this operator. Three "Not for this
page" answers in a week on the same task mute it until somebody un-mutes it in
the console. That last rule is the one that keeps the panel quiet for a person
who has decided.

### 8. Questions

A run that needs an answer posts a `question` and pauses. The entry shows the
sentence, one button per known choice, and a text field for anything else.
Answering resumes the run, and the answer is the operator's own message. The
question stays in the ledger, buttons gone, as the record of who decided.

### 9. Failures

A failure is a card with a sentence and one button, never a colour and never
a paragraph. The sentence says what stopped it. The button says the one thing
that helps:

- the escalation table has a next medium: "Try another way"
- the run is waiting on a value: "Ask me" (opens a question)
- the tab it needs is closed: "Open the page"
- the browser cannot be reached: the chip expands; the card says "nothing is
  lost"

### 10. Type, spacing, radius, motion

- **Type scale**, in px: 11 (mono captions), 12.5 (body, most of the panel),
  14 (entry titles), 17 (the "Running" and "Done" words on a run and a
  result, Space Grotesk, medium). Nothing larger. The panel is 360 to 420 px
  beside a dense application; a 24 px heading in it is a poster.
- **Line length** stays under 60 characters at 360 px; the ledger's gutter is
  44 px for the time rail and 12 px after it.
- **Spacing** on a 4 px scale: 4, 8, 12, 16, 24. Entries are 12 apart;
  bands are 16 apart.
- **Radius by role**: 6 px on fields and buttons, 10 px on cards, 999 on the
  chip's dot and the profile disc. Not one radius on everything.
- **Motion**, one thing only: a step glyph turning from `●` to `✓` fades over
  180 ms. The nudge's accent line thins over its last fifteen seconds. Nothing
  else animates. `prefers-reduced-motion` turns both off.
- **Focus** is visible on every control, a 2 px accent ring, never removed.

### 11. Copy

Sentence case. Plain verbs. The task's own name, never "the skill". A button
says what happens: "Do the next one", "Run it", "Undo that", "Try another
way". The same words in the ledger and in the console for the same thing. No
"AI", no "learning", no "confidence". A number appears only if the system
measured it.

### 12. Components and files

Extension, all vanilla and without `innerHTML`, as `transcript.js` is:

- `panel/strip.js` — brand row, status chip, profile menu. Owns the four
  expand-yourself cases.
- `panel/ledger.js` — `transcript.js` renamed and grown: the time rail, the
  kinds table above, answered entries. Pure function of a thread to DOM.
- `panel/run-card.js` — the run card, its step rows, `change`, notes, pause
  and stop. Takes a run and a thread message, returns DOM.
- `panel/nudge.js` — fire, three ends, mute rules. Owns the ninety seconds.
- `panel/today.js` — the three numbers.
- `panel/panel.js` — shrinks to wiring: status, thread, refresh, the composer.
  It is 1905 lines today; what stays should be under 500.
- `panel/panel.css` — rewritten to the scale in §10. Same brand variables.
- `background/in-page.js` — the pill beside the banner, in the same shadow
  root.
- `options/` — unchanged in function; its purge and disconnect buttons stay so
  a broken panel still has them.

Backend, small:

- `domain/observation/candidate.py`: `starts_on: str | None`, set by the
  miner from the first page event of the first episode; carried to the skill.
- `domain/chat/thread.py`: the decision kinds in §4 named in one place.
- `application/trigger/`: a matched watch posts a `mail_match` message
  instead of, not as well as, its panel-only offer.
- `application/execution/execute_skill.py`: a `note` on a live run is stored
  on the run; a `change` on a pending step rewrites that step's values and
  records the operator message.
- `GET /v1/threads/current` already returns the thread. `GET /v1/runs/{id}`
  already returns steps and verdicts. `GET /v1/analytics/summary` supplies
  the today line. One new endpoint: `POST /v1/runs/{id}/steps/{index}/values`.

## What this must refuse

- A prompt that stays. A nudge older than ninety seconds with its buttons
  still drawn is a bug with a test.
- Two nudges in one page visit.
- A number nobody measured. No "saves you 30 minutes a week".
- Editing a message to show its outcome. The answer is its own message.
- Running anything because a message says so. The press is the authorisation.
- `innerHTML` anywhere in `panel/`.
- A modal. A nudge, a question, a failure are all entries in the ledger.
- The panel deciding a run's values. It shows them and lets the person change
  them; the values a run uses come back from the server.

## Verification

- `make test-extension`: `ledger.test.mjs` draws each kind in §4 from a fixed
  thread and asserts buttons present, buttons gone after an answer, no
  `innerHTML` in the module source. `nudge.test.mjs` asserts the three ends
  and the once-per-visit rule with a fake clock. `run-card.test.mjs` asserts a
  pending step is changeable and a sent step is not.
- `tests/browser`: the nudge pill appears in a real Chrome when a watched tab
  lands on `starts_on`, and is gone after navigation.
- By eye, at 360 and 420 px, every state in the brief's table of nine, plus:
  a live run with a question, a mail match with an empty field, a nudge in
  its last fifteen seconds, a failed run with "Try another way".
- A screenshot of each, kept under `docs/design/panel/`, so the next redesign
  starts from what was built rather than what was described.

## Out of scope

- The console. Its own spec follows, reusing the ledger as a React component.
- Anything the planner does with a note. Sub-plan 3.
- Chains offered as one job. Sub-plan 4.
- A light theme. There is none.
