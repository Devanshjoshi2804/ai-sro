// A run a mail started: the mail arrived, this job was noticed, and how it went.
//
// The only card for that mail on Home. The run's own performing and finished
// cards stand aside for it, and any offer card for the same mail has already
// been ended by the worker -- one mail, one card.
//
// Pure: a run in, DOM out. `textContent` only -- the subject and the sender are
// the mail's words. What a press means is the caller's.

function mailClock(at) {
  const when = new Date(at || "");
  if (Number.isNaN(when.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(when.getHours())}:${pad(when.getMinutes())}`;
}

// How long the run took, in plain words: " in 24 s", " in 1 min 5 s".
function mailTook(run) {
  const took = Math.round((new Date(run.finished_at) - new Date(run.started_at)) / 1000);
  if (!Number.isFinite(took) || took < 0) return "";
  const minutes = Math.floor(took / 60);
  const seconds = took % 60;
  return ` in ${[minutes ? `${minutes} min` : "", seconds || !minutes ? `${seconds} s` : ""].filter(Boolean).join(" ")}`;
}

function mailLine(text, className = "detail") {
  const said = document.createElement("p");
  said.className = className;
  said.textContent = text;
  return said;
}

// What the run is waiting on a person for, if anything: the question a
// running run is parked on (`asking`), or the question that names this run --
// a refused value is asked for after the run has ended. "Running…" is only
// for a run nobody is holding up (QA 2026-09-30: PJ26's card said Running
// while its save waited on the operator).
function mailWaitsOn(run, question) {
  if (question?.text) return question.text;
  return run.status === "running" ? run.asking || "" : "";
}

function mailHowItWent(run, waits) {
  if (waits) return `Needs you: ${waits}`;
  if (run.status === "running")
    return run.doing ? `Running — ${run.doing}…` : "Running…";
  const at = mailClock(run.finished_at);
  if (run.status === "held")
    return `Completed${at ? ` at ${at}` : ""}${mailTook(run)}.`;
  const why = [...(run.steps || [])]
    .reverse()
    .find((step) => step.outcome === "failed" && step.reason)?.reason;
  // "Not created" is true only of a create that failed; a delete, an update or
  // a stopped run did not finish, which says nothing about a record.
  const created = run.status === "failed" && /^create\b/i.test(run.title || "");
  return `${created ? "Not created" : "Did not finish"}: ${why || run.status}.`;
}

/**
 * `live` is the performing run's record when this run is the one performing,
 * for its Watch it run. `questions` are the standing questions; the one naming
 * this run is drawn here. `onOpen(url)` opens a tab; `onAnswer(question, run)`
 * opens where it is answered (`question` null for a run parked on a step);
 * `onReview`, `onStop` and `onDismiss` get the run.
 */
export function mailRunCard(
  run,
  { live = null, questions = [], onOpen, onAnswer, onReview, onStop, onDismiss } = {},
) {
  const mail = run.mail || {};
  // Its own question, never another mail's: every standing one is held.
  const question = questions.find((one) => one.run === run.id) || null;
  const running = run.status === "running";
  const waits = mailWaitsOn(run, question);
  const card = document.createElement("section");
  card.className = "card";
  card.dataset.runId = run.id;
  card.dataset.key = `mail:${run.id}`;
  if (running && !waits) card.dataset.tone = "live";
  else if (run.status !== "held") card.dataset.tone = "attention";

  const heading = document.createElement("h3");
  heading.textContent = mail.subject ? `Mail: ${mail.subject}` : "A mail";
  card.append(heading);

  const arrived = mailClock(mail.arrived);
  card.append(
    mailLine(
      `Arrived${arrived ? ` ${arrived}` : ""}${mail.sender ? ` from ${mail.sender}` : ""}`,
    ),
  );
  const values = Object.entries(run.values || {})
    .filter(([, value]) => String(value ?? "").trim())
    .map(([name, value]) => `${name}: ${value}`)
    .join(" · ");
  card.append(
    mailLine(`Noticed: ${run.title || run.workflow_id}${values ? ` — ${values}` : ""}`),
  );
  card.append(mailLine(mailHowItWent(run, waits), "what"));

  const row = document.createElement("div");
  row.className = "row";
  const press = (label, act, quiet = true) => {
    const button = document.createElement("button");
    button.type = "button";
    if (quiet) button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", () => act(button));
    row.append(button);
  };
  // Only once the question is in a chat to open: without it `onAnswer` can
  // only open the operator's own conversation, which is the wrong one.
  if (waits && question) press("Answer it", () => onAnswer?.(question, run), false);
  if (mail.link) press("Open the mail", () => onOpen?.(mail.link), !waits);
  if (running && live?.liveViewUrl)
    press("Watch it run", () => onOpen?.(live.liveViewUrl));
  press("Review in console", () => onReview?.(run));
  if (running) press("Stop", (button) => onStop?.(run, button));
  press("Dismiss", () => onDismiss?.(run));
  card.append(row);
  return card;
}
