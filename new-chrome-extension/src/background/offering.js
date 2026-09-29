// What the last few gestures do to the offer that is open.
//
// The arrival nudge asks "you have done this here before, shall I?" from the
// address alone. This asks it from the work itself: two gestures into a proven
// job, the rig's shape says which job it is and what has already been typed
// into it, so the offer that lands is "finish *this*" rather than "start
// something like it".
//
// Pure -- the worker does the reading, the storing and the showing around it --
// which is what makes the whole of it testable without a browser.

import { fire, page as pageOf } from "../panel/nudge.js";
import { covered, diverged, match } from "./recognise.js";

export function decideOffer({ tail, shapes, open, origin, page = null, now }) {
  const rigOpen = open && open.source === "rig" && open.state === "open" && open.k > 0 ? open : null;
  // Leaving the path ends it. Carrying the job further does not: `diverged`
  // counts every prefix at least as long as the offer's as still on it, so the
  // match below is free to find the longer `k` and replace the offer with it.
  if (rigOpen && diverged(tail, rigOpen, shapes)) return { replace: null, end: "diverged" };
  // A tail that reached the end of the job is a job the operator finished:
  // the offer ends, so a press can never hand Steel a count behind what they did.
  const rigShape = rigOpen && shapes.find((s) => s.id === rigOpen.workflowId);
  if (rigShape && covered(tail, rigShape.shape).k >= rigShape.shape.length)
    return { replace: null, end: "did_it" };
  const found = match(tail, shapes);
  if (!found) return { replace: null, end: null };
  // A shorter or equal prefix is the same offer said again, and an offer that
  // redraws itself on every keystroke is a flicker, not a prompt.
  if (rigOpen && found.k <= rigOpen.k) return { replace: null, end: null };
  const shape = shapes.find((s) => s.id === found.workflowId);
  const replace = fire(
    // The page the gestures were made on, not the shape's `starts_on`: a job
    // whose recording opens with a click on the screen before is done here,
    // and leaving here -- or "Always on this page" -- is about here.
    { id: found.workflowId, title: found.title,
      starts_on: page ? pageOf(page) : shape?.starts_on || origin,
      source: "rig", workflow_id: found.workflowId, k: found.k,
      since: found.since, through: found.through,
      values: found.values, missing: found.missing, parameters: found.parameters,
      writes: shape?.writes || [] },
    now,
  );
  return { replace, end: null };
}
