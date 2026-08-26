# Design brief — the AI-SRO side panel

Hand this whole file to whoever (or whatever) is doing the design. It is the
context, the constraints and the list of screens. It deliberately contains no
visual direction: what it fixes is *what has to be on the screen and why*.

---

## 1. What the product is, in one paragraph

Warehouse operators do the same tasks in a warehouse management system (Blue
Yonder) all day: close a wave, adjust a short-shipped line, create a supplier,
answer "where is this order". AI-SRO watches them work in their own browser,
notices what they repeat, and turns two demonstrations of one task into a
**skill** — a replayable, reviewable recipe. A skill starts out only able to
rehearse, earns the right to write, and can end up running unattended on a
schedule or when an email arrives. Nothing about a task is guessed: what it is,
what varies in it, and whether it worked are all read off recorded evidence, and
where the evidence does not say, the system refuses rather than assumes.

## 2. Who is looking at it

- **An operator** in a warehouse, in a browser tab of a WMS that looks like it
  was designed in 2009, with forty other things to do. Not technical. Will not
  read a paragraph. Judges the product by whether it saves them a task today.
- **A supervisor**, who has to approve that a piece of automation may write to
  the warehouse, and who is accountable when it writes the wrong thing.

## 3. The surface being designed

A **Chrome side panel**, docked beside the tab the operator is working in.

- Width is roughly **360–420 px** and the operator can drag it wider. Height is
  the window's height. It is *tall and narrow* — a phone-shaped column beside a
  desktop app.
- It is always beside a page. It knows which host that page is on, and that is
  the one thing no other screen in the product knows.
- Below the panel's own controls it currently embeds the web console (the
  full-size review app) in an iframe. Whether that should continue is one of
  the questions this brief asks.

## 4. What only the panel can do

This is the test for whether something belongs here:

1. **Start and stop a demonstration of the tab beside it.** The operator does
   the task normally; the extension records gestures, network calls, the
   accessibility tree and screenshots.
2. **Say what has been captured while it is happening.** A recording that is
   capturing nothing looks exactly like one that is capturing everything until
   it is stopped.
3. **Offer the tasks noticed on *this* host** — "you have done this four times
   this week; shall I learn it?"
4. **Stop a run** that is being performed in this browser right now.
5. **Say when this browser is not connected, not observing, or unreachable**,
   and what to do about it.
6. **Delete the last hour of evidence** — an operator's own escape hatch.

Everything else (reviewing a skill's steps, promoting it, reading past runs,
scheduling) is the console's job and is not panel work.

## 5. The states that must be designed

Each of these is a real state of the same panel. Today several of them are one
grey sentence.

| # | State | What is true | What the operator must be able to do |
|---|---|---|---|
| 1 | **Not connected** | No credential; nothing is recorded; nothing can be taught | Connect: open settings, paste a token issued by whoever runs the deployment |
| 2 | **Connected, nothing noticed here** | Observing this host, no repeated task seen yet | Understand that repetition is what makes a task appear, and start a demonstration if they already know what they want |
| 3 | **Connected, tasks noticed** | One or more candidate tasks for this host, each with how often and how long | Read what it thinks the task is, teach it, or dismiss it |
| 4 | **Recording a demonstration** | A demonstration is being captured from the tab beside the panel | See it is working (elapsed, how much captured), stop and save, or discard |
| 5 | **Just saved a demonstration** | Evidence stored; it may or may not be enough to induce a skill | Know whether a second demonstration is needed, and start it |
| 6 | **A run is performing here** | A skill is driving this browser now — possibly triggered elsewhere | See what it is doing and stop it |
| 7 | **Paused** | The operator paused observation, or the deployment did | Resume (or understand they cannot) |
| 8 | **Cannot reach the deployment** | Channel closed, API unreachable, token expired | Know that nothing is being lost, and what to do |
| 9 | **Two tasks suggested as one job** | The system thinks a task on this host and one on another are two halves of one job | Answer whether they are, and teach them as one |

## 6. Hard constraints

- **The operator's own browser is the point.** Anything that opens a browser
  somewhere else is a different product and must never look like the same
  button. (This was a real bug: the panel offered "Teach on Blue Yonder" which
  opened a server-side browser and streamed it back, next to a "Start teaching"
  that recorded the operator's own tab.)
- **Nothing may claim more than the evidence says.** No "learned!" when what
  happened was "one demonstration stored, one more needed". No progress bar for
  work that is not measurable.
- **Writes are somebody's decision.** Anything that will change the warehouse
  says who authorised it, and a supervisor must be able to see that in review.
- **Recording is visible.** While observation is on, that fact is on screen. The
  operator can pause it and delete the last hour without asking anybody.
- **No modal dialogs.** The panel is docked beside real work; a modal steals it.
- **Everything must survive at 360 px** with the system font. Long hostnames,
  long task titles, long refusal sentences.
- **It has to work in monochrome-ish palettes.** The WMS beside it is dense and
  colourful; the panel should not compete with it.
- **Failure states are first-class.** Roughly half the states above are failures
  or absences. They are the ones that get designed last and seen first.

## 7. What is wrong with it today

Screenshots attached separately, but in words:

1. **Everything is the same weight.** A status sentence, two buttons, a section
   heading, an embedded application. Nothing says what to look at.
2. **The embedded console dominates.** Two thirds of the panel is a full-size
   app squeezed into a column: a chat, a card, a composer, a footer. It has its
   own affordances that compete with the panel's.
3. **Failures are grey sentences** with nothing to press. "not connected",
   "the console did not accept this browser", "no console configured".
4. **The demonstration flow has no shape.** Press *Start teaching*, then
   nothing until you press stop. (Just improved: it now counts elapsed time and
   things captured. It still does not say what happens next.)
5. **No sense of progress towards a skill.** A task needs two demonstrations,
   then review, then promotion through rehearsal into writing. None of that
   ladder is visible from the panel, so the operator never sees the thing they
   are working towards.

## 8. What good would look like

- An operator who has never seen it can tell, in three seconds: is it watching,
  what system am I on, and what is the one thing I could do next.
- A demonstration feels like a recording: something visibly accumulates, and
  stopping produces a result you can look at.
- A refusal is a card with a sentence and a button, not a colour.
- The panel is quiet while the operator works, and loud exactly twice: when it
  has noticed something worth automating, and when something is wrong that only
  they can fix.

## 9. Deliverables asked for

1. The nine states above, at 360 px and at 420 px.
2. A component inventory: status line, primary action, attention card, task
   card, recording state, run state, footer.
3. A recommendation on the embedded console: keep it, scope it to one screen,
   or drop it and link out to the full console in a tab.
4. Type scale, spacing and colour tokens that survive next to a dense WMS.

## 10. What not to do

- Do not design a dashboard. This is a tool used beside other work.
- Do not add an onboarding tour. The states above are the onboarding.
- Do not invent metrics ("87% confidence"). If a number appears it has to come
  from evidence the system actually holds.
- Do not design a chat as the primary surface here. Chat belongs in the console;
  the panel is about the tab beside it.
