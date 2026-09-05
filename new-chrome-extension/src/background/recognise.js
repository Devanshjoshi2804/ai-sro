// recognise.js
// Which proven job the operator has just started, decided from the last few
// gestures on the tab. Arithmetic on the shape the rig serves -- no model, no
// waiting for the once-a-minute flush -- so an offer can land on the second
// gesture, not a minute after it.
//
// Only a strict prefix is offered: a tail that already ends with the whole
// shape is a job the operator has finished, and there is nothing left to
// offer. So a two-step job is never offered by prefix -- arriving on its page
// covers that one.

export const K_TAIL = 12;
export const K_OFFER_AFTER = 2;

const key = (triple) => triple.join(" ");

/** The tail with one more gesture. Scrolls are noise in a prefix and are dropped. */
export function tailWith(tail, entry) {
  if (entry.triple[1] === "anon|scroll") return tail;
  return [...tail, entry].slice(-K_TAIL);
}

function endsWith(tail, prefix) {
  if (prefix.length > tail.length) return false;
  const from = tail.length - prefix.length;
  return prefix.every((triple, i) => key(triple) === key(tail[from + i].triple));
}

/** Values typed so far for the parameters the prefix has reached. */
export function valuesFrom(tail, shape, k) {
  const values = {};
  const missing = [];
  const from = tail.length - k;
  for (const p of shape.parameters || []) {
    const entry = p.at !== null && p.at < k ? tail[from + p.at] : null;
    if (entry && !entry.secret && entry.value != null) values[p.name] = entry.value;
    else missing.push(p.name);
  }
  return { values, missing };
}

/** The best job this tail is a prefix of, or null. */
export function match(tail, shapes, { origin }) {
  let best = null;
  for (const shape of shapes) {
    if (!shape.shape?.length || shape.shape[0][0] !== origin) continue;
    for (let k = Math.min(shape.shape.length - 1, tail.length); k >= K_OFFER_AFTER; k--) {
      if (!endsWith(tail, shape.shape.slice(0, k))) continue;
      if (!best || k > best.k || (k === best.k && (shape.held_runs || 0) > best.heldRuns)) {
        best = { workflowId: shape.id, title: shape.title, k, heldRuns: shape.held_runs || 0, shape };
      }
      break;
    }
  }
  if (!best) return null;
  const { values, missing } = valuesFrom(tail, best.shape, best.k);
  return {
    workflowId: best.workflowId,
    title: best.title,
    k: best.k,
    values,
    missing,
    parameters: (best.shape.parameters || []).map((p) => p.name),
  };
}

/**
 * Whether the tail has left the job's path. Carrying the job further is not
 * divergence: any prefix of the shape at least as long as the offer's still
 * counts as on the path, up to and including the whole of it.
 */
export function diverged(tail, offer, shapes) {
  const shape = shapes.find((s) => s.id === offer.workflowId);
  if (!shape) return true;
  for (let j = offer.k; j <= shape.shape.length; j++) {
    if (endsWith(tail, shape.shape.slice(0, j))) return false;
  }
  return true;
}
