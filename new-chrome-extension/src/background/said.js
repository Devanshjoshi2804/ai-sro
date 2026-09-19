// What this browser did, kept where a person can still read it afterwards.
//
// The backend's half of this is `sro.infrastructure.telemetry.whose`: every
// line says whose work it was about, and a deployment collects them. This side
// has had nothing at all. Fifty-six `console` calls write to a service
// worker's devtools console, and that console dies with the worker -- which
// this extension now knows happens constantly, because a worker evicted
// between two commands is what lost a run its tab and cost an operator an
// evening of sign-in loops.
//
// So what matters is written down. An operator says "I pressed it and nothing
// happened", and the answer is in their own browser rather than gone.
//
// **Kept selectively, not everything.** A storage write per command is the
// cost this codebase already refuses for a write per keystroke, and a ring
// full of "sent ui.perform" is a ring with no room for the failure. So every
// call reaches the console and only what a person would want afterwards --
// a refusal, a fault, the start and end of a run -- is persisted.
//
// **Ids, never values.** The same rule the backend's plane holds: a run id, a
// tab id, a command kind and an error kind say who and where; a typed value, a
// password and a page's text say what, and none of them belong in a buffer
// that exists to be handed to somebody else.

import { state } from "./state.js";

/** How many entries the ring holds.
 *
 * Two hundred is a working day of the things worth keeping -- runs, refusals,
 * faults -- at the rate a single operator produces them, and about 40KB, which
 * is nothing against `chrome.storage.local`'s quota. It is NOT sized for one
 * entry per command, which is the shape this deliberately does not have. */
export const K_KEPT = 200;

/** What a kept entry may be attributed to. Closed, for the reason the
 * backend's `KNOWN` is closed: a list that can hold anything ends up holding a
 * customer's name, and this buffer exists to be handed to somebody. */
const ABOUT = ["run", "tab", "kind", "device", "workflow", "step", "error"];

/** Everything kept, oldest first. */
export async function said() {
  return (await state.said()) || [];
}

/** Write one line, to the console always and to the ring when it is worth
 * keeping afterwards.
 *
 * `level` is "info" | "warn" | "error". Anything but "info" is kept without
 * being asked: a warning nobody can read after the worker dies is a warning
 * that was never written. `keep` forces an info line into the ring, for the
 * few that a person reading afterwards needs -- a run starting, a run ending.
 */
export async function say(level, what, about = {}, { keep = false } = {}) {
  const mine = {};
  for (const key of ABOUT) {
    if (about[key] !== undefined && about[key] !== null) mine[key] = about[key];
  }
  const line = { at: Date.now(), level, what, ...mine };
  const shown = `[sro] ${what}${Object.keys(mine).length ? ` ${JSON.stringify(mine)}` : ""}`;
  if (level === "error") console.error(shown);
  else if (level === "warn") console.warn(shown);
  else console.log(shown);
  if (level === "info" && !keep) return line;
  try {
    const held = await said();
    await state.setSaid([...held, line].slice(-K_KEPT));
  } catch {
    // A ring that cannot be written is not a reason to fail the thing being
    // logged about. The console still has it.
  }
  return line;
}

/** Forget everything kept. For the panel's own "clear", and for sign-out --
 * the buffer is this operator's, and it leaves with them. */
export async function forgetSaid() {
  await state.setSaid([]);
}
