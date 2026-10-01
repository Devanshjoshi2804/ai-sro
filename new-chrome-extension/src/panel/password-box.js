// The box a run asks its password in.
//
// A Steel run that cannot sign in parks on a question that names the account
// (`question.origin`, `question.username`); this draws the answer where the
// person already is, on the run's card. It is the same box `run-card.js` draws
// for a step the extension drove, with the same rules: the field is never read
// back, never defaulted, never written to `chrome.storage`, and is emptied on
// the press. What is typed leaves through `onPassword` -- the service worker's
// one-way trip to the backend -- and nowhere else.
//
// Pure: a question in, DOM out. `textContent` only.

/** The run's standing password question, when a box can answer it: one that
 * names its account. An older question that does not is refused by the
 * backend, so drawing a box for it would be a button that cannot work. */
export function standingPassword(run) {
  const asked = run?.question;
  return asked?.kind === "password" && asked.origin && asked.username
    ? asked
    : null;
}

/**
 * `onPassword({ runId, questionId, value, keep })` resolves `{ ok }` or
 * `{ ok: false, error }`. "Save for next time" keeps it for every later run of
 * the account; "Just this once" hands it to this run alone.
 */
export function passwordBox(question, { runId, onPassword }) {
  const box = document.createElement("div");
  box.className = "password";
  const said = document.createElement("p");
  said.className = "note";
  said.textContent = `This job needs your password for ${question.origin} (${question.username}).`;
  const field = document.createElement("input");
  field.type = "password";
  // Not `current-password`: a manager offering to fill this would offer the
  // credential for the PANEL's own origin, not the system being signed into.
  field.autocomplete = "off";
  field.placeholder = "password";
  const press = (label, keep) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (!keep) button.className = "quiet";
    button.addEventListener("click", async () => {
      const value = field.value;
      field.value = "";
      if (!value) return;
      button.disabled = true;
      const sent = await onPassword({
        runId,
        questionId: question.id,
        value,
        keep,
      });
      button.disabled = false;
      said.textContent = sent?.ok
        ? "Sent. The run carries on."
        : `That could not be saved: ${sent?.error || "the vault did not answer"}`;
    });
    return button;
  };
  box.append(
    said,
    field,
    press("Save for next time", true),
    press("Just this once", false),
  );
  return box;
}
