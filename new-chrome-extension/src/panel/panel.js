// The surface docked beside the system the operator is working in.
//
// Two halves. The strip and the task list are native, because everything on
// them needs `chrome.*` or needs to know which tab this is: teaching is a
// control you want beside the page being taught, a run driving this browser has
// to be stoppable while it happens, and "tasks you keep doing *here*" is a
// question a page that does not know the host cannot ask.
//
// The rest is the console in a frame. One implementation of each review screen,
// so nothing drifts -- and the credential it needs is handed to it, because
// Chrome partitions storage for framed contexts and the console cannot see the
// token from its own tab.

const $ = (id) => document.getElementById(id);

async function ask(message) {
  const answer = await chrome.runtime.sendMessage(message);
  if (answer?.error) throw new Error(answer.error);
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

// -- the strip ---------------------------------------------------------------

function render(status) {
  $("headline").dataset.on = String(status.capturing);
  $("headline").textContent = status.capturing
    ? "Observing this browser."
    : `Not observing — ${status.because}.`;

  $("pause").textContent = status.paused ? "Resume" : "Pause";
  $("pause").disabled = Boolean(status.serverPaused);

  $("teach").textContent = status.teaching ? "Stop and save" : "Start teaching";
  $("teach").disabled = !status.capturing;
  $("teaching-state").textContent = status.teaching
    ? "teaching — do the task, then stop"
    : "";

  const run = status.performing;
  $("run").hidden = !run;
  if (run) {
    const seconds = Math.round((Date.now() - run.since) / 1000);
    $("run-state").textContent = `a run is performing here — ${run.kind}, ${seconds}s`;
  }

  $("trouble").textContent = status.lastError || "";
  $("purge").disabled = !status.deviceId;
  return status;
}

async function refresh() {
  return render(await ask({ kind: "status" }));
}

$("pause").addEventListener("click", async () => {
  const status = await ask({ kind: "status" });
  render(await ask({ kind: "set-paused", paused: !status.paused }));
});

$("teach").addEventListener("click", async () => {
  $("teach").disabled = true;
  try {
    const status = await ask({ kind: "status" });
    if (status.teaching) {
      const stopped = await ask({ kind: "teach-stop" });
      $("teaching-state").textContent = stopped.summary
        ? `saved — ${stopped.summary.frame_count ?? 0} steps`
        : "stopped";
    } else {
      const tab = await beside();
      if (!tab) throw new Error("open the system you want to teach in this tab first");
      // Named, not guessed: this panel is docked beside the tab being taught,
      // which is the one thing the options page could never say.
      await ask({ kind: "teach-start", tabId: tab.id, label: tab.title });
    }
  } catch (error) {
    $("teaching-state").textContent = error.message;
  }
  await refresh();
});

$("abort").addEventListener("click", async () => {
  const status = await ask({ kind: "status" });
  if (!status.performing) return;
  await ask({ kind: "abort-run", runId: status.performing.runId });
  // What is already inside the page finishes; this stops the next step, which
  // is what the button says.
  $("run-state").textContent = "stopping — the step already sent will finish";
  await refresh();
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

  $("candidates-note").textContent = candidates.length
    ? ""
    : `nothing noticed on ${host} yet — it takes a few doings of the same task`;
  $("candidates").replaceChildren(...candidates.map(row));
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
    `done ${candidate.times_seen} times · ` +
    `${Math.round(candidate.median_duration_ms / 1000)}s each · ` +
    `${candidate.minutes_so_far} minutes so far`;

  item.append(title, facts);

  // Read-only, deliberately: acting on one is a decision that belongs to a
  // person and to a screen that does not exist yet.
  for (const join of candidate.joins || []) {
    const suggestion = document.createElement("p");
    suggestion.className = "note";
    suggestion.textContent =
      join.kind === "workflow"
        ? `looks like half of one job with another task — ${join.because}`
        : `looks like the same task as another — ${join.because}`;
    item.append(suggestion);
  }

  const actions = document.createElement("div");
  actions.className = "row";

  const teach = document.createElement("button");
  teach.type = "button";
  teach.textContent = "Teach";
  teach.addEventListener("click", () => taught(candidate, item));

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "quiet";
  dismiss.textContent = "Not worth it";
  dismiss.addEventListener("click", async () => {
    await ask({ kind: "dismiss-candidate", id: candidate.id, reason: "not worth automating" });
    await here();
  });

  actions.append(teach, dismiss);
  item.append(actions);
  return item;
}

async function taught(candidate, item) {
  const said = document.createElement("p");
  said.className = "note";
  item.append(said);
  try {
    const answer = await ask({ kind: "teach-candidate", id: candidate.id });
    if (!answer.needs_demonstration) {
      said.textContent = "learned from what was already watched";
      await here();
      return;
    }
    // The loop the console cannot close: it can say the passive evidence was
    // too thin, and only this can start a demonstration in your browser.
    said.textContent = `${answer.because || "the evidence was too thin"} — show me once:`;
    const show = document.createElement("button");
    show.type = "button";
    show.textContent = "Show me once";
    show.addEventListener("click", async () => {
      const tab = await beside();
      if (!tab) {
        said.textContent = "open the system in this tab first";
        return;
      }
      await ask({ kind: "teach-start", tabId: tab.id, label: candidate.title });
      await refresh();
    });
    item.append(show);
  } catch (error) {
    said.textContent = error.message;
  }
}

// -- the console -------------------------------------------------------------

async function frameTheConsole() {
  const { consoleUrl, token } = await ask({ kind: "panel-console" });
  if (!consoleUrl) {
    $("console-note").textContent = "no console configured — set one in Settings";
    return;
  }
  if (!token) {
    $("console-note").textContent = "connect this browser in Settings";
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
  // only health check there is. Say the likely cause rather than a certain one.
  setTimeout(() => {
    if ($("console-note").textContent === "opening the console…") {
      $("console-note").textContent =
        `the console did not accept this browser — is ${chrome.runtime.id} in its ` +
        "allowed extension origins?";
    }
  }, 5000);
}

// ponytail: polled while the panel is open rather than pushed from the worker.
// A few storage reads a second is cheap and has no lifecycle edge cases; make
// it a broadcast if it is ever felt.
setInterval(() => {
  if (document.visibilityState === "visible") void refresh();
}, 2000);

void refresh();
void here();
void frameTheConsole();
