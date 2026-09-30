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
  if (question?.run === run.id && question.text) return question.text;
  return run.status === "running" ? run.asking || "" : "";
}

function mailHowItWent(run, waits) {
  if (waits) return `Needs you: ${waits}`;
  if (run.status === "running")
    return run.doing ? `Running — ${run.doing}…` : "Running…";
  const at = mailClock(run.finished_at);
  if (run.status === "held") return `Completed${at ? ` at ${at}` : ""}.`;
  const why = [...(run.steps || [])]
    .reverse()
    .find((step) => step.outcome === "failed" && step.reason)?.reason;
  return `Not created: ${why || run.status}.`;
}

/**
 * `live` is the performing run's record when this run is the one performing,
 * for its Watch it run. `question` is the standing question, drawn here when
 * it names this run. `onOpen(url)` opens a tab; `onAnswer(question, run)`
 * opens where it is answered (`question` null for a run parked on a step);
 * `onReview`, `onStop` and `onDismiss` get the run.
 */
export function mailRunCard(
  run,
  { live = null, question = null, onOpen, onAnswer, onReview, onStop, onDismiss } = {},
) {
  const mail = run.mail || {};
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
  if (waits)
    press(
      "Answer it",
      () => onAnswer?.(question?.run === run.id ? question : null, run),
      false,
    );
  if (mail.link) press("Open the mail", () => onOpen?.(mail.link), !waits);
  if (running && live?.liveViewUrl)
    press("Watch it run", () => onOpen?.(live.liveViewUrl));
  press("Review in console", () => onReview?.(run));
  if (running) press("Stop", (button) => onStop?.(run, button));
  press("Dismiss", () => onDismiss?.(run));
  card.append(row);
  return card;
}
