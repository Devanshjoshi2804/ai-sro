// What this browser did, in words, for the log on the other end.
//
// `service-worker.js` has said things for a while: a line goes in a buffer,
// the heartbeat carries it up, and the backend writes it beside its own. Its
// own argument, which stands -- `run_workflow` narrates every rung it climbs
// and the deployment's log reads like a transcript; the browser half of the
// same run was a black box whose only voice was a service worker console that
// cannot be reached from a server, from another machine, or by somebody
// debugging at two in the morning.
//
// Two things are added here and nothing is taken away.
//
// **The command surface can say things now.** `say` lived in the worker, and
// `commands.js` -- which is where every refusal and every fault actually
// happens -- cannot import the module that imports it. Eleven command cases
// each refused in silence.
//
// **A line says what it is about.** It was free text, so a refusal read
// `no tab for https://keycloak...` and a reader had to guess which run, which
// tab and which command. The backend learned the same lesson this week and
// its half of it is `sro.infrastructure.telemetry.whose`: the ids ride
// alongside rather than being written into the sentence by whoever remembered.
//
// The wire is unchanged on purpose. `HeartbeatRequest.said` is a list of
// strings and there are browsers in the field that will go on sending
// strings, so this renders the ids onto the end of the line rather than
// shipping an object the backend would refuse. The rendering is the same
// shape the backend's own `Plainly` formatter uses, so both halves of one run
// read alike.

import { serially } from "./serially.js";
import { state } from "./state.js";

/** How many lines wait for the next beat.
 *
 * The backend bounds this too -- `K_SAID_LINES` -- and a browser is not a
 * trusted writer: a loop in here must not be able to fill a disk. The two
 * numbers are the same number and must stay so; a browser that buffers more
 * than the door accepts is a browser whose extra lines are refused whole. */
export const MAX_SAID = 50;

/** How much of one line is kept. The backend truncates again on the way in. */
const MAX_CHARS = 300;

/** What a line may be attributed to.
 *
 * Closed, for the reason the backend's `KNOWN` is closed: a list that can hold
 * anything ends up holding a customer's name, and these lines leave the
 * browser on the next beat. A value a caller passes under any other name is
 * dropped rather than trusted.
 */
const ABOUT = ["run", "tab", "kind", "device", "workflow", "step", "error"];

/** Everything waiting to go up, oldest first. */
export async function said() {
  return (await state.said()) || [];
}

/** Say one line: to the console always, and into the buffer that ships.
 *
 * `level` is "info" | "warn" | "error". Anything but "info" is buffered
 * without being asked -- a warning nobody can read after the worker dies is a
 * warning that was never written -- and `keep` buffers an ordinary line that a
 * person would want afterwards anyway.
 *
 * Never throws and never blocks the caller on storage: this is a line about
 * something that already happened, and a narration that can break the thing it
 * narrates is worse than silence.
 */
export async function say(level, what, about = {}, { keep = false } = {}) {
  const mine = ABOUT.filter(
    (key) => about[key] !== undefined && about[key] !== null,
  ).map((key) => `${key}=${about[key]}`);
  const line = `${level} ${what}${mine.length ? ` [${mine.join(" ")}]` : ""}`;
  if (level === "error") console.error(`[sro] ${line}`);
  else if (level === "warn") console.warn(`[sro] ${line}`);
  else console.log(`[sro] ${line}`);
  if (level === "info" && !keep) return line;
  try {
    // Through the one lock, because two refusals a millisecond apart both read
    // the buffer and both wrote it back, and the second took the first with
    // it. The failure is invisible: the line simply is not there.
    await serially(async () => {
      const held = await said();
      await state.setSaid([...held, line.slice(0, MAX_CHARS)].slice(-MAX_SAID));
    });
  } catch {
    // Nothing. See above.
  }
  return line;
}

/** This browser telling the story of what it decided.
 *
 * What `service-worker.js` has always done, under a name that says so. Every
 * one of these is a decision a person reading a run afterwards wants -- an
 * offer withdrawn, a reply waited for, a mail lost -- so they are kept without
 * being asked, which is what the single-argument `say` did before it grew a
 * level.
 *
 * `say` is the other thing: a level, for a refusal or a fault, from the
 * command surface where those actually happen.
 */
export async function narrate(what, about = {}) {
  return say("info", what, about, { keep: true });
}
