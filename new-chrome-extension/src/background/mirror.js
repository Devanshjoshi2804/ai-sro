/**
 * Post a copy of an upload to the rig, if one is configured.
 *
 * Deliberately silent: the rig is a second reader, not a second source of
 * truth. upload.js drops queued rows on a permanent 4xx from the backend, and
 * a rig that is down, slow, or refusing must never be able to reach that
 * decision.
 */
export async function mirrorTo(base, token, path, { body, form, fetcher = fetch } = {}) {
  if (!base) return;
  try {
    const options = { method: "POST", headers: {} };
    if (token) options.headers.Authorization = `Bearer ${token}`;
    if (form) {
      options.body = form;
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    await fetcher(`${base}${path}`, options);
  } catch {
    // The rig is optional. Its silence is not the extension's problem.
  }
}
