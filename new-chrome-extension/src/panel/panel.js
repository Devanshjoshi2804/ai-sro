// The surface docked beside the system the operator is working in.
//
// Everything above the console frame is native, because everything on it needs
// `chrome.*` or needs to know which tab this is: teaching is a control you want
// beside the page being taught, a run driving this browser has to be stoppable
// while it happens, and "tasks you keep doing *here*" is a question a page that
// does not know the host cannot ask.
//
// What is drawn is one card per thing that is true, in the order somebody
// should deal with it. Not connected outranks not observing, which outranks a
// closed channel; a demonstration in progress outranks all of them, because
// while one is running the panel is about that and nothing else.

const $ = (id) => document.getElementById(id);

async function ask(message) {
  const answer = await chrome.runtime.sendMessage(message);
  if (answer?.error) {
    // This panel reloads with its own page; the worker behind it does not.
    // After an update, a new panel talks to the old worker and every new
    // message comes back "no such message" -- which reads as a broken button
    // rather than as a browser that has not picked the update up yet.
    if (String(answer.error).startsWith("no such message")) {
      throw new Error(
        "this browser is still running an older copy of the extension — " +
          "reload it at chrome://extensions, then try again",
      );
    }
    throw new Error(answer.error);
  }
  return answer;
}

/** The tab this panel is docked beside.
 *
 * The active one, which is the whole point of a panel. Where that is not an
 * ordinary page -- a settings tab in front, or this page opened as a tab rather
 * than docked -- the last ordinary page in the same window, which is the same
 * rule the worker falls back to and the same answer an operator would give.
 */
async function beside() {
  const ordinary = (tab) => /^https?:/.test(tab?.url || "");
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (ordinary(active)) return active;
  const inThisWindow = await chrome.tabs.query({ currentWindow: true });
  return (
    inThisWindow
      .filter(ordinary)
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))[0] || null
  );
}

function hostOf(url) {
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    return "";
  }
}

function clock(since) {
  const seconds = Math.max(0, Math.round((Date.now() - since) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

// -- building a card ---------------------------------------------------------

/** One thing that is true, and what can be done about it.
 *
 * A panel that reports a problem without a way out is a panel people stop
 * reading, so a card that has an action carries it; one that does not says why
 * in a sentence somebody can act on elsewhere.
 */
function card({ title, says, metrics, notes, stage, progress, tone, actions = [] }) {
  const holder = document.createElement("section");
  holder.className = "card";
  if (tone) holder.dataset.tone = tone;

  if (title) {
    const heading = document.createElement("h3");
    heading.textContent = title;
    holder.append(heading);
  }
  if (says) {
    const line = document.createElement("p");
    line.textContent = says;
    holder.append(line);
  }
  if (metrics) {
    const line = document.createElement("p");
    line.className = "metrics";
    line.textContent = metrics;
    holder.append(line);
  }
  // A line each, for a card that has several small facts rather than one --
  // the values a mail gave up, where each of them came from.
  for (const note of notes || []) {
    const line = document.createElement("p");
    line.className = "metrics";
    line.textContent = note;
    holder.append(line);
  }
  if (progress) {
    const bar = document.createElement("div");
    bar.className = "progress";
    for (let step = 0; step < progress.of; step += 1) {
      const segment = document.createElement("span");
      segment.dataset.done = String(step < progress.done);
      bar.append(segment);
    }
    holder.append(bar);
  }
  if (stage) {
    const line = document.createElement("p");
    line.className = "stage";
    line.textContent = stage;
    holder.append(line);
  }

  const row = document.createElement("div");
  row.className = "row";
  for (const action of actions) {
    if (!action) continue;
    const button = document.createElement("button");
    button.type = "button";
    if (!action.primary) button.className = "quiet";
    button.textContent = action.label;
    button.disabled = Boolean(action.disabled);
    button.addEventListener("click", () => action.act(button));
    row.append(button);
  }
  if (row.childElementCount) holder.append(row);
  return holder;
}

// -- the states --------------------------------------------------------------

function render(status) {
  const cards = [];

  if (!status.deviceId) {
    cards.push(
      card({
        title: "Not connected",
        says:
          "This browser has no credential. Nothing is recorded and no task can be "
          + "taught until it is connected to your deployment.",
        tone: "attention",
        actions: [{ label: "Connect", primary: true, act: () => chrome.runtime.openOptionsPage() }],
      }),
    );
  } else if (status.teaching) {
    cards.push(recording(status));
  } else {
    cards.push(watching(status));
  }

  // Before the run and after the state card: it is the only thing here waiting
  // on the person. Not while teaching, because then the panel is about the
  // demonstration and nothing else -- the offer keeps.
  if (!status.teaching) for (const offer of status.offers || []) cards.push(offering(offer));

  if (status.performing) cards.push(performing(status));
  for (const trouble of troubles(status)) cards.push(trouble);

  $("cards").replaceChildren(...cards);
  // Green means this tab -- the one the panel is docked beside -- is being
  // recorded. A dot that went green for "capture is enabled somewhere" told an
  // operator their work was being kept when nothing in front of them was.
  const watchedHere = (status.watched || []).some((entry) => entry.tabId === tabHere.tabId);
  $("where").dataset.state = status.teaching
    ? "recording"
    : status.capturing && watchedHere
      ? "observing"
      : status.deviceId
        ? "unknown"
        : "unknown";

  // While a demonstration is being recorded the panel is about that and
  // nothing else, and none of it applies to a browser that is not connected.
  $("here").hidden = Boolean(status.teaching) || !status.deviceId;
  $("ask").disabled = !status.deviceId;
  $("purge").disabled = !status.deviceId;
  return status;
}

/** A demonstration, while it is being recorded.
 *
 * It counts out loud. A recording that is capturing nothing looks exactly like
 * one that is capturing everything until it is stopped, and finding out then
 * means doing the task again.
 */
function recording(status) {
  const since = Date.parse(status.teaching.startedAt || "") || Date.now();
  const seen = status.queued ?? 0;
  return card({
    title: "Recording your demonstration",
    says: "Do the task normally. Gestures, network calls and the page structure are being captured.",
    metrics: `${clock(since)} · ${seen} thing${seen === 1 ? "" : "s"} seen`,
    tone: "live",
    actions: [
      { label: "Stop and save", primary: true, act: (button) => stopTeaching(button) },
      { label: "Discard", act: (button) => stopTeaching(button, { discard: true }) },
    ],
  });
}

function watching(status) {
  const paused = status.paused || status.serverPaused;
  if (paused) {
    return card({
      title: "Paused",
      says: status.serverPaused
        ? "Observation is paused for everyone on this deployment."
        : "Nothing is being recorded until you resume.",
      actions: [pauseAction(status)],
    });
  }

  const watched = status.watched || [];
  const mine = watched.find((entry) => entry.tabId === tabHere.tabId) || null;
  const others = watched.length - (mine ? 1 : 0);
  const elsewhere = others
    ? ` ${others} other tab${others === 1 ? " is" : "s are"} being watched.`
    : "";

  // Nothing is watched unless somebody said so. The alternative -- recording
  // every tab and sorting it out later -- is what put a console's own polling
  // into the evidence and a mail client one policy edit away from it.
  if (!mine) {
    return card({
      title: "Not watching this tab",
      says:
        (tabHere.host
          ? `Nothing in ${tabHere.host} is being recorded.`
          : "Open the system you work in.") +
        " Watch a tab and everything in it is evidence -- its calls, its screens," +
        " wherever it navigates." +
        elsewhere,
      tone: "attention",
      actions: [
        {
          label: "Watch this tab",
          primary: true,
          disabled: !status.capturing || !tabHere.tabId,
          act: (button) => setWatch(button, true),
        },
        pauseAction(status),
      ],
    });
  }

  return card({
    title: "Watching this tab",
    says:
      `Everything you do in ${mine.host || "this tab"} is evidence. What you repeat` +
      " becomes a task worth offering; teach one deliberately at any time." +
      elsewhere,
    metrics: `since ${clock(mine.since)}`,
    actions: [
      {
        label: "Start teaching",
        primary: true,
        disabled: !status.capturing,
        act: (button) => startTeaching(button),
      },
      { label: "Stop watching", act: (button) => setWatch(button, false) },
      pauseAction(status),
    ],
  });
}

function pauseAction(status) {
  return {
    label: status.paused ? "Resume" : "Pause",
    disabled: Boolean(status.serverPaused),
    act: async () => {
      const now = await ask({ kind: "status" });
      render(await ask({ kind: "set-paused", paused: !now.paused }));
    },
  };
}

async function setWatch(button, on) {
  button.disabled = true;
  try {
    await ask({ kind: on ? "watch-tab" : "unwatch-tab", tabId: tabHere.tabId, url: tabHere.url });
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

/** A run driving this browser, possibly started somewhere else.
 *
 * Stoppable from here because this is where somebody sees it happening: a run
 * started by a schedule is otherwise a cursor moving on its own.
 */
function performing(status) {
  const run = status.performing;
  const done = Number.isFinite(run.step) ? run.step : null;
  const total = run.of && done !== null && done <= run.of ? run.of : null;
  return card({
    title: run.skill ? `“${run.skill}” is running` : "A run is performing here",
    says:
      (run.because || "Started elsewhere") +
      (done === null ? "." : total ? `. Step ${done} of ${total}.` : `. Step ${done}.`),
    metrics: `${run.kind} · ${clock(run.since)}`,
    stage: run.stage || null,
    progress: total ? { done, of: total } : null,
    tone: "live",
    actions: [
      {
        label: "Stop this run",
        primary: true,
        act: async (button) => {
          button.disabled = true;
          await ask({ kind: "abort-run", runId: run.runId });
          // What is already inside the page finishes; this stops the next step,
          // which is what the button says.
          button.textContent = "stopping — the step already sent will finish";
          await refresh();
        },
      },
      { label: "Details in console", act: () => openConsole(`/runs/${run.runId}`) },
    ],
  });
}

/** A mail this browser recognised, and the one press that acts on it.
 *
 * Nothing runs unasked, so this card is the whole of what a watch does by
 * itself: it says what it found and waits. What a person needs in order to
 * decide is which task, what was read out of the mail as against what was
 * already on the task, and what recognised it.
 *
 * The rule, not the mail. The sender and the subject that decided this were
 * read in the frame and forgotten there -- and the operator can see the mail,
 * because this panel is docked beside it. What they cannot see is which of
 * their own terms caught it, so that is what is written here.
 *
 * Everything on this card was read in this browser and has been nowhere else.
 * The values went up once, to be told what the task would run with; nothing
 * was stored there and nothing is stored by pressing beyond the run's own
 * parameters, which is where a run's values have always lived.
 */
function offering(offer) {
  const named = offer.skill || offer.skillId;
  const read = offer.read || {};
  const missing = offer.missing || [];
  const because = (offer.terms || [])
    .map((term) => `${term.field} contains “${term.contains}”`)
    .join(" and ");
  return card({
    title: `A mail matched “${named}”`,
    says: because
      ? `Recognised in ${offer.host}: ${because}.`
      : `Recognised in ${offer.host}.`,
    // Which value came from the mail and which was already on the task. The
    // difference is the decision: one of them is what somebody just wrote to
    // this operator, and the other is what they set up themselves.
    notes: Object.entries(offer.values || {}).map(
      ([name, value]) =>
        `${name}: ${value} — ${name in read ? "read from the mail" : "already on the task"}`,
    ),
    metrics: `${clock(offer.at)} ago`,
    // Said before the press rather than after it. The same names the fire
    // itself would skip on, so a card that cannot run says so instead of
    // starting a run that stops a moment later where nobody is looking.
    stage: missing.length
      ? `Nothing said ${missing.join(", ")}, so this one cannot run.`
      : offer.skipped || null,
    tone: missing.length ? "attention" : null,
    actions: [
      {
        label: "Run it",
        primary: true,
        disabled: Boolean(missing.length),
        act: async (button) => {
          button.disabled = true;
          try {
            const fired = await ask({ kind: "watch-fire", offerId: offer.id });
            said(
              fired.run_id
                ? `started — “${named}” is running`
                : `nothing started: ${fired.skipped}`,
            );
          } catch (error) {
            said(error.message);
          }
          await refresh();
        },
      },
      {
        label: "Not now",
        act: async (button) => {
          button.disabled = true;
          await ask({ kind: "drop-offer", offerId: offer.id });
          said("dismissed — the mail is untouched and nothing ran");
          await refresh();
        },
      },
    ],
  });
}

/** Everything wrong at once, in the order somebody should deal with it.
 *
 * These were four grey sentences in four places, each of which said what was
 * true and none of which said what to do.
 */
function troubles(status) {
  const cards = [];
  if (status.deviceId && !status.capturing && !status.paused && !status.serverPaused) {
    cards.push(card({ title: "Not observing", says: `${status.because}.`, tone: "attention" }));
  }
  if (status.deviceId && status.channel !== "open") {
    cards.push(
      card({
        title: "This browser cannot be reached",
        says:
          `The command channel is ${status.channel}. A run started from the console or a `
          + "schedule cannot act here until it opens; nothing already captured is lost.",
        tone: "attention",
      }),
    );
  }
  if (status.lastError) {
    cards.push(card({ title: "Last error", says: status.lastError, tone: "attention" }));
  }
  return cards;
}

async function startTeaching(button) {
  button.disabled = true;
  try {
    const tab = await beside();
    if (!tab) throw new Error("open the system you want to teach in this tab first");
    // Named, not guessed: this panel is docked beside the tab being taught,
    // which is the one thing the options page could never say.
    await ask({ kind: "teach-start", tabId: tab.id, label: tab.title });
  } catch (error) {
    said(error.message);
  }
  await refresh();
}

async function stopTeaching(button, { discard = false } = {}) {
  button.disabled = true;
  try {
    const stopped = await ask({ kind: "teach-stop", discard });
    if (discard) {
      said("discarded — nothing was kept");
    } else {
      const steps = stopped.summary?.frame_count ?? 0;
      said(`saved — ${steps} step${steps === 1 ? "" : "s"}. Teach it once more to prove what varies.`);
    }
  } catch (error) {
    said(error.message);
  }
  await refresh();
  await here();
}

/** A sentence under the cards, for what just happened. */
function said(words) {
  $("candidates-note").textContent = words;
}

async function refresh() {
  const status = await ask({ kind: "status" });
  // What a run driving this browser actually is: the worker knows its id and
  // that it is happening, and the run's own record knows what it is called, how
  // far through it is and which rung it is allowed to be on.
  if (status.performing) {
    try {
      const run = await ask({ kind: "run", runId: status.performing.runId });
      const skill = await ask({ kind: "skill", skillId: run.skill_id });
      const version = (skill.versions || []).find((each) => each.version === run.skill_version);
      status.performing = {
        ...status.performing,
        skill: skill.name || null,
        stage: run.stage || null,
        step: Array.isArray(run.steps) ? run.steps.length : null,
        // How many steps the version has, which is what makes "step 3 of 6"
        // answerable. A looping skill performs more positions than it has
        // steps, so this is a floor rather than a promise -- and the card says
        // "step 3" without the total when they disagree.
        of: version?.steps?.length ?? null,
        because: run.requested_by ? `Started by ${run.requested_by}` : null,
      };
    } catch {
      // A run the panel cannot read is still a run the panel can stop.
    }
  }
  return render(status);
}

/** The system this panel is docked beside. */
/** The host the task list below was built for, so switching tabs rebuilds it.
 * Without this the list is whatever was in front when the panel opened, which
 * reads as "nothing noticed on this system" while the line above it names a
 * different system entirely. */
let showing = null;

/** The tab this panel is docked beside -- the one every card is about. */
let tabHere = { tabId: null, host: "", url: "" };

async function whereWeAre() {
  const tab = await beside();
  const host = hostOf(tab?.url || "");
  tabHere = { tabId: tab?.id ?? null, host, url: tab?.url || "" };
  $("where").textContent = host || "no system open in this window";
  if (host !== showing) {
    showing = host;
    await here();
    await refresh();
  }
}

function openConsole(path = "/console") {
  ask({ kind: "panel-console" }).then(({ consoleUrl }) => {
    if (consoleUrl) void chrome.tabs.create({ url: `${consoleUrl}${path}` });
  });
}

$("open-console").addEventListener("click", () => openConsole());

$("ask").addEventListener("click", () => {
  // The console's chat, framed here rather than in a tab: asking for a task is
  // the one console screen that belongs beside the work.
  const console_ = $("console");
  console_.hidden = !console_.hidden;
  $("ask").textContent = console_.hidden ? "Ask for a task" : "Hide the console";
  if (!console_.hidden && !$("frame").src) void frameTheConsole();
});

$("purge").addEventListener("click", async () => {
  // Two clicks, in the page rather than a modal: a dialog raised here blocks
  // the very worker being asked to do the deleting.
  if ($("purge").dataset.armed !== "1") {
    $("purge").dataset.armed = "1";
    $("purge").textContent = "Really delete the last hour?";
    setTimeout(() => {
      $("purge").dataset.armed = "";
      $("purge").textContent = "Delete the last hour";
    }, 5000);
    return;
  }
  $("purge").dataset.armed = "";
  $("purge").textContent = "Delete the last hour";
  try {
    const gone = await ask({ kind: "purge", hours: 1 });
    $("purged").textContent =
      `deleted ${gone.events} events in ${gone.batches} batches, ` +
      `and ${gone.artifacts ?? 0} screenshots`;
    await here();
  } catch (error) {
    $("purged").textContent = `nothing was deleted: ${error.message}`;
  }
});

$("options").addEventListener("click", (event) => {
  event.preventDefault();
  chrome.runtime.openOptionsPage();
});

// -- tasks you keep doing here ----------------------------------------------

async function here() {
  const tab = await beside();
  const host = hostOf(tab?.url || "");
  if (!host) {
    $("candidates").replaceChildren();
    $("candidates-note").textContent = "open the system you work in to see its tasks";
    return;
  }

  let candidates;
  try {
    candidates = await ask({ kind: "candidates", host });
  } catch (error) {
    $("candidates-note").textContent = error.message;
    return;
  }

  // Only what is still a question. The endpoint answers with every status --
  // dismissed and taught included, because the miner reads them all so it does
  // not re-offer what somebody said no to -- and a panel that offered "Teach"
  // on a dismissed one would be offering a button the backend refuses.
  const offerable = candidates.filter((candidate) => candidate.status === "new");

  $("candidates-note").textContent = offerable.length
    ? ""
    : `nothing noticed on ${host} yet — it takes a few doings of the same task`;
  $("candidates").replaceChildren(...offerable.map(row));
}

function row(candidate) {
  const item = document.createElement("li");

  const title = document.createElement("p");
  title.className = "title";
  title.textContent = candidate.title;
  if (candidate.named_by_model) {
    // Said out loud: a sentence a model wrote is not a fact about the task.
    const mark = document.createElement("span");
    mark.className = "by-model";
    mark.textContent = " — named by a model";
    title.append(mark);
  }

  const facts = document.createElement("p");
  facts.className = "note";
  facts.textContent =
    `Seen ${candidate.times_seen} times · ` +
    `about ${Math.round(candidate.median_duration_ms / 1000)}s each · ` +
    `${candidate.minutes_so_far} minutes so far`;

  item.append(title, facts);

  for (const join of candidate.joins || []) item.append(suggestion(candidate, join));

  const actions = document.createElement("div");
  actions.className = "row";

  const teach = document.createElement("button");
  teach.type = "button";
  teach.textContent = "Teach it";
  teach.addEventListener("click", () => taught(candidate, item));

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "quiet";
  dismiss.textContent = "Not worth it";
  dismiss.addEventListener("click", async () => {
    try {
      await ask({ kind: "dismiss-candidate", id: candidate.id, reason: "not worth automating" });
      await here();
    } catch (error) {
      // Said on the row rather than thrown into nothing: a click that does
      // nothing and explains nothing is how somebody decides the panel is
      // broken.
      facts.textContent = error.message;
    }
  });

  actions.append(teach, dismiss);
  item.append(actions);
  return item;
}

/** What a model noticed about this candidate, and the two words a person can
 * answer it with.
 *
 * The answer is the point. A suggestion nobody can answer accumulates on a
 * screen until the screen is ignored, and every sweep re-asks it -- so until
 * somebody says, it is a question, and once they have, it is a fact with their
 * name on it and the miner stops asking.
 */
function suggestion(candidate, join) {
  const holder = document.createElement("div");
  holder.className = "joined";

  const said_ = document.createElement("p");
  said_.className = "note";
  const what =
    join.kind === "workflow"
      ? "looks like half of one job with another task"
      : "looks like the same task as another";
  said_.textContent = join.answered
    ? `${join.answered === "same" ? "one job with another task" : "a different task"} — ` +
      `${join.answered_by} said so`
    : `${what} — ${join.because}`;
  holder.append(said_);

  const actions = document.createElement("div");
  actions.className = "row";

  if (join.answered) {
    // The only answer anything can act on. `same` about a workflow means the
    // two are one job done in two systems -- which no single candidate can
    // represent, so until this button existed the answer changed nothing.
    if (join.kind === "workflow" && join.answered === "same") {
      const merge = document.createElement("button");
      merge.type = "button";
      merge.textContent = "Teach as one";
      merge.addEventListener("click", async () => {
        merge.disabled = true;
        try {
          const answer = await ask({
            kind: "teach-together",
            id: candidate.id,
            otherId: join.other_id,
          });
          said_.textContent = answer.needs_demonstration
            ? answer.because || "the evidence for the two halves was too thin"
            : "learned as one skill";
          await here();
        } catch (error) {
          said_.textContent = error.message;
          merge.disabled = false;
        }
      });
      actions.append(merge);
      holder.append(actions);
    }
    return holder;
  }

  for (const [label, answer] of [
    ["Same task", "same"],
    ["Different", "different"],
  ]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", async () => {
      try {
        await ask({
          kind: "answer-join",
          id: candidate.id,
          otherId: join.other_id,
          // `kind` is taken by the message itself, and a join has one too.
          joinKind: join.kind,
          answer,
        });
        await here();
      } catch (error) {
        said_.textContent = error.message;
      }
    });
    actions.append(button);
  }
  holder.append(actions);
  return holder;
}

async function taught(candidate, item) {
  const note = document.createElement("p");
  note.className = "note";
  item.append(note);
  try {
    const answer = await ask({ kind: "teach-candidate", id: candidate.id });
    if (!answer.needs_demonstration) {
      note.textContent = "learned from what was already watched";
      await here();
      return;
    }
    // The loop the console cannot close: it can say the passive evidence was
    // too thin, and only this can start a demonstration in your browser.
    note.textContent = `${answer.because || "the evidence was too thin"} — show me once:`;
    const show = document.createElement("button");
    show.type = "button";
    show.textContent = "Show me once";
    show.addEventListener("click", async () => {
      const tab = await beside();
      if (!tab) {
        note.textContent = "open the system in this tab first";
        return;
      }
      await ask({ kind: "teach-start", tabId: tab.id, label: candidate.title });
      await refresh();
    });
    item.append(show);
  } catch (error) {
    note.textContent = error.message;
  }
}

// -- the console -------------------------------------------------------------

async function frameTheConsole() {
  const { consoleUrl, token } = await ask({ kind: "panel-console" });
  if (!token || !consoleUrl) {
    // Already said once, at the top, with the button that fixes it. Saying it
    // again down here would be a second complaint about one thing.
    $("console").hidden = true;
    return;
  }

  const origin = new URL(consoleUrl).origin;
  const frame = $("frame");

  // The console announces itself once its listener exists. Posting on `load`
  // instead would race its hydration and lose the credential intermittently,
  // which is the worst way for a handshake to fail.
  window.addEventListener("message", (event) => {
    if (event.origin !== origin) return;
    if (event.data?.kind === "sro.ready") {
      // Addressed to the console's own origin, never "*": a wildcard hands the
      // credential to whatever the frame has navigated to.
      frame.contentWindow?.postMessage({ kind: "sro.credential", token }, origin);
      return;
    }
    if (event.data?.kind === "sro.credential.ok") $("console-note").textContent = "";
  });

  $("console-note").textContent = "opening the console…";
  frame.src = `${consoleUrl}/console?embedded=1`;
  frame.hidden = false;

  // A cross-origin frame does not report its own failures, so the reply is the
  // only health check there is -- and until it arrives the frame is a grey
  // rectangle that looks like a broken page. Show what to do instead of it, and
  // keep showing it: a setup step nobody is told about twice is a setup step
  // nobody does.
  setTimeout(() => {
    if ($("console-note").textContent === "opening the console…") {
      frame.hidden = true;
      refused(consoleUrl);
    }
  }, 5000);
}

/** What to do when the console will not accept this browser.
 *
 * The console decides which extension may frame it and hand it a credential --
 * a deployment that accepted any extension would accept one somebody else
 * installed. So this is a line of configuration, and the panel is where
 * somebody finds out it is missing. It says which line, where, and hands it
 * over ready to paste.
 */
function refused(consoleUrl) {
  const holder = $("console-refused");
  holder.hidden = false;
  holder.replaceChildren();

  const origin = `chrome-extension://${chrome.runtime.id}`;
  const said_ = document.createElement("p");
  said_.className = "note";
  said_.textContent = `${consoleUrl} did not accept this browser. It only frames extensions it has been told about.`;

  const what = document.createElement("code");
  what.className = "fix";
  what.textContent = `NEXT_PUBLIC_EXTENSION_ORIGINS=${origin}`;

  const where = document.createElement("p");
  where.className = "note";
  where.textContent = "Put that in the console's environment (frontend/.env.local) and restart it.";

  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "Copy the line";
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(what.textContent);
    copy.textContent = "copied";
    setTimeout(() => (copy.textContent = "Copy the line"), 2000);
  });

  const again = document.createElement("button");
  again.type = "button";
  again.className = "quiet";
  again.textContent = "Try again";
  again.addEventListener("click", () => {
    holder.hidden = true;
    $("console-note").textContent = "";
    void frameTheConsole();
  });

  const row_ = document.createElement("div");
  row_.className = "row";
  row_.append(copy, again);
  holder.append(said_, what, where, row_);
  $("console-note").textContent = "";
}

// ponytail: polled while the panel is open rather than pushed from the worker.
// A few storage reads a second is cheap and has no lifecycle edge cases; make
// it a broadcast if it is ever felt.
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  void refresh();
  void whereWeAre();
}, 2000);

void refresh();
void whereWeAre();
