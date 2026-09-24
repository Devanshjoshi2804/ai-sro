// What is on the screen, when it is not the thing the step is about.
//
// A run that cannot find its control says `control_not_found: no control
// matched`. That is true, and it is silent about the only question worth
// asking -- somebody reading it goes looking for a broken selector, and the
// selector is usually fine. Measured on the deployment 2026-09-18: a session
// expired, and every run for the next several minutes blamed a missing tab
// item while a login form sat on the screen.
//
// So the browser says what IS there. Two things so far, and the rule they are
// both held to is the one the server-side session check already keeps:
//
// **STRUCTURE, never words.** A password box means a login; the word
// "password" means a warehouse screen that mentions passwords. A dialog
// element means a dialog; the word "error" means a column header. Any
// heuristic on words fires on a working screen eventually, and a run that
// stopped saying "you are signed out" in front of a form that was fine would
// be worse than one that said nothing at all.
//
// The one place words are carried is a dialog's own text, and that is not a
// heuristic -- it is the evidence. A modal saying "Record already exists" is
// the whole answer to why a Save did nothing, and this deployment has one:
// `Existing Carriers duplicate check is SERVER-side: the form accepts the
// click and only then shows an in-app 'Record already exists' modal.`

/** A login page, by the box only a login has. */
export const A_LOGIN =
  'input[type="password"], input[autocomplete="current-password"]';

/** A dialog, by the things that ARE dialogs rather than by what they say.
 *
 * `<dialog open>` and `role="dialog"` are the page declaring it; the two class
 * names are the two frameworks this deployment's systems are built with, and
 * they are here because ExtJS does not set the role. A class list is a weaker
 * signal than a role and it is still structure: nothing types `.x-message-box`
 * into a column header.
 */
export const A_DIALOG =
  'dialog[open], [role="dialog"], [role="alertdialog"], .x-message-box, .modal.show';

/** A page that has not finished, by the things that say so.
 *
 * `document.readyState` is the page's own word for it and costs nothing. The
 * two selectors are for the case it cannot answer: a single-page application
 * finished loading its document minutes ago and is now fetching the screen,
 * and `readyState` has said `complete` the whole time. `role="progressbar"` is
 * the page declaring it; `.x-mask-loading` is what ExtJS puts over a panel it
 * is filling, which is the framework these systems are built with.
 */
export const STILL_COMING =
  '[role="progressbar"], .x-mask-loading, .x-mask.x-mask-msg';

/** How much of what a dialog says to carry back.
 *
 * Enough for "Record already exists" and for the sentence under it. A modal
 * with two paragraphs in it is one whose first line is the answer, and the
 * rest is a step record nobody reads. */
export const K_SAID = 400;

/**
 * What the page has to say about itself, read inside it.
 *
 * Handed to `executeScript` as-is, so it reads `document` and closes over
 * nothing: the function is serialised and re-created in the page, where a
 * reference to anything in this file would arrive undefined. The selectors
 * come in as arguments for the same reason.
 *
 * Everything here is optional. A page that answers nothing is a page nothing
 * is known about, which is exactly what the run assumed before this existed.
 */
export function whatIsOnThisPage(said) {
  const shown = (el) =>
    el.offsetParent !== null || el.getClientRects?.().length;
  const seen = (css) => [...document.querySelectorAll(css)].filter(shown);

  const dialog = seen(said.dialog)[0];
  const logins = seen(said.login);
  return {
    signed_out: logins.length > 0,
    // Whether a login box on screen is EMPTY -- the fact, never the value. A
    // form that comes back empty right after a password was submitted is the
    // system refusing it; one still holding what was typed is a submit still
    // in flight. The run engine latches the password on the first and waits
    // on the second, so a refused password is never typed twice.
    credential_empty: logins.some((box) => !box.value),
    // Still coming, which is the one of these a run can do something about
    // other than stop: what a half-drawn screen needs is a moment, and every
    // rung of the ladder spent on it is a model call answering a question
    // about a page that was not there yet.
    loading:
      document.readyState !== "complete" || seen(said.loading).length > 0,
    // The innermost text and not the outer box's: a dialog wrapper often
    // contains the whole page behind it, and "what the dialog said" would then
    // be the screen read out.
    dialog: dialog
      ? String(dialog.innerText || dialog.textContent || "")
          .replace(/\s+/g, " ")
          .trim()
          .slice(0, said.cap)
      : "",
  };
}
