// Every call to the backend. See docs/14-extension-protocol.md.

import { state } from "./state.js";

export class ApiError extends Error {
  constructor(status, problem) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.status = status;
    this.problem = problem;
  }
}

async function call(path, { method = "GET", body, form, signal } = {}) {
  const [base, token] = await Promise.all([state.apiUrl(), state.token()]);
  // A multipart body names its own content type, boundary and all, and a
  // Content-Type set here would replace it with one the boundary is missing
  // from -- which every parser reads as a body with no parts in it.
  const response = await fetch(`${base}${path}`, {
    method,
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: form !== undefined ? form : body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401) {
    // The same rule the console follows: a credential that is not accepted is
    // dropped, so the operator lands back on the paste screen instead of every
    // later call failing quietly.
    await state.setToken("");
    throw new ApiError(401, { detail: "that credential was not accepted" });
  }
  if (!response.ok) {
    throw new ApiError(response.status, await response.json().catch(() => null));
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  register: (label, extensionVersion) =>
    call("/v1/agents/register", {
      method: "POST",
      body: { label, extension_version: extensionVersion },
    }),

  heartbeat: (deviceId, beat) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/heartbeat`, {
      method: "POST",
      body: beat,
    }),

  observations: (batch) => call("/v1/observations", { method: "POST", body: batch }),

  /** A screenshot or an oversized body, uploaded beside the batch it
   * illustrates. `form` carries device_id, batch_id, kind, file and the
   * frame_index that says which gesture it followed. */
  artifact: (form) => call("/v1/observations/artifacts", { method: "POST", form }),

  policy: () => call("/v1/agents/policy"),

  /** What this browser is watching its operator's mail for. Asked for here
   * because a watch is evaluated in the browser that has the mailbox open and
   * nowhere else -- no mail is ever sent to the backend, so the rule comes
   * the other way. */
  watches: (deviceId) => call(`/v1/agents/${encodeURIComponent(deviceId)}/watches`),

  /** A mail was recognised. The body is the values the operator marked and
   * nothing else -- not the subject, not the sender, not why. What comes back
   * is the offer; nothing has started. */
  watchMatched: (deviceId, triggerId, values) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/watches/${encodeURIComponent(triggerId)}/matched`,
      { method: "POST", body: values },
    ),

  /** The press. The operator saw the offer and said do it, so the values go up
   * again -- nothing was kept at the match, and this browser is where they
   * live. What comes back is the run, or why none started. */
  watchFire: (deviceId, triggerId, values) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/watches/${encodeURIComponent(triggerId)}/fire`,
      { method: "POST", body: values },
    ),

  /** Start a demonstration this browser will fill. Nothing is opened on the
   * server: the operator is already in front of the system. */
  startRecording: (deviceId, label) =>
    call("/v1/recordings", { method: "POST", body: { device_id: deviceId, label } }),

  /** Seal it. The backend assembles the frames from what this browser
   * uploaded, so everything must have gone up before this is called. */
  finishRecording: (recordingId, abandonReason = null) =>
    call(`/v1/recordings/${encodeURIComponent(recordingId)}/finish`, {
      method: "POST",
      // A reason means abandon rather than seal. The evidence is kept either
      // way -- what changes is that nothing will be induced from it.
      body: abandonReason ? { abandon_reason: abandonReason } : {},
    }),

  /** One run, for the panel to say what is happening in this browser.
   *
   * The worker knows a run is driving a tab and knows its id; what it is called,
   * which rung it is on and how far through it is are the run's own record. */
  run: (runId) => call(`/v1/runs/${encodeURIComponent(runId)}`),

  /** One skill, for the name and the shape of the version being run. */
  skill: (skillId) => call(`/v1/skills/${encodeURIComponent(skillId)}`),

  /** Tasks this operator keeps doing on one system. The panel asks about the
   * tab it is docked beside; the host is what makes it that question. */
  candidates: (host) =>
    call(`/v1/candidates?seen_at_least=3&host=${encodeURIComponent(host)}`),

  teachCandidate: (id) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/teach`, { method: "POST", body: {} }),

  /** Two candidates a person has said are one job, taught as one skill. Each
   * time the operator did both halves in a row is one demonstration of it. */
  teachTogether: (id, otherId) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/teach-together`, {
      method: "POST",
      body: { other_id: otherId },
    }),

  /** What a person says two candidates are to each other. The model may only
   * ever have suggested it. */
  answerJoin: (id, otherId, kind, answer) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/joins`, {
      method: "POST",
      body: { other_id: otherId, kind, answer },
    }),

  dismissCandidate: (id, reason) =>
    call(`/v1/candidates/${encodeURIComponent(id)}/dismiss`, {
      method: "POST",
      body: { reason },
    }),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, { method: "DELETE" }),
};
