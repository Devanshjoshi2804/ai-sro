// Filling this system's own login page, in the operator's own browser.
//
// The one command in this extension that carries a secret, in its own file
// because of it: everything here is about a value that must be typed into a
// page and exist nowhere else afterwards.
//
// **The rules it is carried under are the ones the rest of the system keeps.**
// The value arrives in the command, is typed, and is never stored, never
// logged, never written to `chrome.storage`, and never put in a result. What
// comes back says what was DONE -- "entered the username", "submitted" -- and
// nothing about what was typed. The backend scrubs the command it recorded
// with `without_secrets` for the same reason.
//
// **Why here at all.** `KeepSessionsOpen` already signs systems back in before
// their sessions die, and its one driver drives a hosted browser over a
// debugger url. The runs that matter drive the operator's own Chrome, which
// nothing could sign in -- so a session that expired mid-shift left a run
// stopped and a person with no way to carry on but to do the whole thing by
// hand. Measured on the deployment 2026-09-18.
//
// **Written against the shape of a login**, not one vendor's markup: a page
// with a password box wants a password, a page with only a text box wants an
// identifier. The same four selectors the hosted driver reads, kept in step
// with it deliberately -- two drivers that disagree about what a login looks
// like are two systems to debug the day one of them signs in to the wrong
// realm, which is a thing that has already happened once.

/** Where a login keeps its parts. Mirrors `infrastructure/steel/sign_in.py`. */
export const SIGN_IN = {
  password: 'input[type="password"]:not([disabled])',
  identifier:
    'input[type="email"]:not([disabled]), input[type="text"]:not([disabled]), input[type="tel"]:not([disabled])',
  submit:
    'button[type="submit"]:not([disabled]), input[type="submit"]:not([disabled]), button#next, button#continue',
  mfa: "input[autocomplete='one-time-code'], input[name*='otp' i], input[name*='mfa' i], input[id*='verification' i]",
};

/**
 * What runs inside the page.
 *
 * **Handed to `executeScript` as-is**, which is why it reads `document` rather
 * than taking one: the function is serialised and re-created inside the page,
 * where a closure over anything in this file would arrive as an undefined
 * name. So it takes only what can be sent -- the values and the selectors --
 * and there is one copy of this rather than one here and one inlined at the
 * call, which are two copies to keep in step.
 *
 * A test drives it the same way the page does: the fake document this
 * extension's tests already install is the `document` it reads.
 *
 * **Both boxes before either submit.** Keycloak puts the username and the
 * password on one form, and a driver that filled whichever it found first
 * submitted a password with no username -- five times, because the page came
 * back empty and it did the same thing again.
 *
 * **A second factor is refused rather than attempted.** A code sent to a phone
 * has no answer in a vault, and pretending otherwise leaves somebody watching
 * a browser time out.
 */
export function fillTheLoginForm(said) {
  const seen = (css) =>
    [...document.querySelectorAll(css)].find(
      (el) => el.offsetParent !== null || el.getClientRects?.().length,
    );
  if (seen(said.where.mfa)) return { mfa: true, did: [] };

  const did = [];
  const fill = (css, value) => {
    const box = seen(css);
    if (!box || !value) return false;
    // The events a framework listens for. A value assigned without them is a
    // box that looks full to a person and empty to React, which submits blank.
    box.focus?.();
    box.value = value;
    box.dispatchEvent(new Event("input", { bubbles: true }));
    box.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  };
  if (fill(said.where.identifier, said.username))
    did.push("entered the username");
  if (fill(said.where.password, said.password))
    did.push("entered the password");

  const go = seen(said.where.submit);
  if (go) {
    go.click();
    did.push("submitted");
  }
  return { mfa: false, did, submitted: Boolean(go) };
}

/**
 * What the extension answers with, given what the page reported.
 *
 * Separate from the driving so the refusals are readable on their own: a page
 * that took nothing is not a login page this can drive, and answering "done"
 * about it would have the run retry a step against a screen nothing changed.
 */
export function whatTheSignInCameTo(answer, failure) {
  if (answer?.mfa)
    return failure(
      "not_actionable",
      "this system asks for a second factor, which no stored credential can answer. " +
        "Sign in by hand and the run will carry on.",
    );
  if (!(answer?.did || []).length)
    return failure(
      "not_actionable",
      "nothing on this page took a username or a password",
    );
  return {
    ok: true,
    result: { did: answer.did, submitted: Boolean(answer.submitted) },
  };
}
