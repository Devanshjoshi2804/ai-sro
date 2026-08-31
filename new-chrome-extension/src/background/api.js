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
  const [base, token, secret] = await Promise.all([
    state.apiUrl(),
    state.token(),
    state.deviceSecret(),
  ]);
  // A multipart body names its own content type, boundary and all, and a
  // Content-Type set here would replace it with one the boundary is missing
  // from -- which every parser reads as a body with no parts in it.
  const response = await fetch(`${base}${path}`, {
    method,
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      // Two things, because they answer two questions. The credential says
      // which tenant is asking; it cannot say which browser, and every
      // device-scoped path is `/v1/agents/{device_id}/...` -- one of which
      // fires a run in a live warehouse. Sent on every call rather than on the
      // four that check it: it goes to the same backend either way, and a list
      // of which endpoints are allowed to see it is a list that goes stale.
      ...(secret ? { "X-Device-Secret": secret } : {}),
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

  /** Watch this host too, beyond what the tenant excludes by default. */
  grantHost: (deviceId, host) =>
    call(`/v1/agents/${encodeURIComponent(deviceId)}/grants`, {
      method: "POST",
      body: { host },
    }),

  revokeHost: (deviceId, host) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/grants/${encodeURIComponent(host)}`,
      { method: "DELETE" },
    ),

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

  /** What a sentence asks for. Ranks the whole taught library every time --
   * there is no field on this request to restrict it to one skill, and the
   * panel does not invent one: a sentence offered against one candidate that
   * names a different taught task is answered about that task. */
  resolveIntent: (utterance) => call("/v1/intent/resolve", { method: "POST", body: { utterance } }),

  /** The press. Promotes the version a preview just showed and starts it in
   * the operator's own browser in one call -- see ADR 014 and
   * `RunFromPreview`. Refused for a looped skill with a sentence written for
   * an operator to read, which the panel shows rather than swallows. */
  runFromPreview: (skillId, parameters, deviceId, intent) =>
    call(`/v1/skills/${encodeURIComponent(skillId)}/runs/from-preview`, {
      method: "POST",
      body: { parameters, device_id: deviceId, intent },
    }),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, { method: "DELETE" }),
};
