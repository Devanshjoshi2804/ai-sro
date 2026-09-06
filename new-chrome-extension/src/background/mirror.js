/**
 * Post a copy of an upload to the rig, if one is configured.
 *
 * Deliberately silent: the rig is a second reader, not a second source of
 * truth. upload.js drops queued rows on a permanent 4xx from the backend, and
 * a rig that is down, slow, or refusing must never be able to reach that
 * decision.
 */
export const MIRROR_TIMEOUT_MS = 5000;

/** Whether a configured mirror base may be posted to at all.
 *
 * What travels this path is a copy of every batch of live customer WMS
 * traffic, and the base comes from a free-text options field with no default
 * host. `mirrorTo` is silent about failure on purpose, so a typo that still
 * parses -- or a pasted `javascript:` or `file:` value -- would send the lot
 * somewhere else with no signal anywhere. The check therefore happens before
 * the fetch rather than being left to the operator's typing.
 *
 * Scheme and shape only, and deliberately no host allowlist: this is a
 * development second reader pointed at whatever the person debugging happens
 * to be running, and an allowlist with nobody named to maintain it is a list
 * that gets switched off the first time it is inconvenient. The other half of
 * this is the options page refusing to *save* a value that fails here, so a
 * rejected configuration is visible where it was typed.
 */
export function isMirrorable(base) {
  if (typeof base !== "string" || !base) return false;
  try {
    const { protocol } = new URL(base);
    return protocol === "http:" || protocol === "https:";
  } catch {
    // Not an absolute URL. A relative path would be resolved against the
    // extension's own origin, which is not a rig.
    return false;
  }
}

/**
 * What became of one mirror, for the options page and nobody else. `sent`
 * is whether a request went out at all; `ok` and `status` are the rig's
 * answer when it gave one; `detail` is its `detail` field when it refused.
 * Returned rather than thrown, and never read by upload.js: a refusal is
 * something a person fixes on the options page, not something that may
 * decide what happens to the backend's rows.
 */
export async function mirrorTo(
  base,
  token,
  path,
  { body, form, fetcher = fetch, timeoutMs = MIRROR_TIMEOUT_MS } = {},
) {
  if (!isMirrorable(base)) return { sent: false };
  try {
    const options = { method: "POST", headers: {} };
    if (token) options.headers.Authorization = `Bearer ${token}`;
    if (form) {
      options.body = form;
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    // Bounded on purpose. A rig that accepts the connection and then never
    // answers is not the same as one that is down: the down case fails fast,
    // this one holds the promise open forever. The caller awaits this, and
    // upload.js does not remove queued rows until it returns -- so an
    // unbounded wait strands batches the backend has already accepted.
    if (typeof AbortSignal !== "undefined" && AbortSignal.timeout) {
      options.signal = AbortSignal.timeout(timeoutMs);
    }
    const response = await fetcher(`${base}${path}`, options);
    if (response?.ok) return { sent: true, ok: true, status: response.status };
    // The rig said no, and said why: 403 for a batch that is not this
    // browser's, 413 for one past its bound, 401 for a token it no longer
    // holds. Silent here as ever, but not lost -- the caller writes it where
    // the options page reads.
    // Only a string `detail`, and only so much of it: it lands in
    // chrome.storage and on the options page, and a rig is not trusted to
    // size it.
    let detail = "";
    try {
      const said = await response.json();
      if (typeof said?.detail === "string") detail = said.detail.slice(0, 200);
    } catch {
      // A refusal with no body is still a refusal with a status.
    }
    return { sent: true, ok: false, status: response?.status ?? 0, detail };
  } catch {
    // The rig is optional. Its silence is not the extension's problem.
    return { sent: false };
  }
}

/** Read the settings and mirror, and never let either fail the caller.
 *
 * The reads have to happen inside this try, not the caller's: `await
 * state.rigUrl()` evaluated at the call site is outside `mirrorTo` entirely,
 * so its own catch cannot see it. chrome.storage rejecting -- an extension
 * context invalidated mid-update -- would otherwise surface as a failed upload
 * of a batch the backend had already stored, and upload.js would keep its rows
 * queued and report an error for work that succeeded.
 */
export async function mirrorSafely(readBase, readToken, path, options) {
  try {
    return await mirrorTo(await readBase(), await readToken(), path, options);
  } catch {
    // Same contract as mirrorTo: the mirror cannot fail the upload.
    return { sent: false };
  }
}
