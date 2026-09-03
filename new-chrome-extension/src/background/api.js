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
  watchMatched: (deviceId, triggerId, values, offerId) =>
    call(
      `/v1/agents/${encodeURIComponent(deviceId)}/watches/${encodeURIComponent(triggerId)}/matched` +
        (offerId ? `?offer=${encodeURIComponent(offerId)}` : ""),
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

  /** The person this ran for says the result was wrong -- reached by pressing
   * "Undo that" or "It's wrong, I'll fix it", things they wanted anyway,
   * which is why it can be trusted the way a survey answer could not be. See
   * `panel.js`'s `undoRun` and `wasWrong`. */
  runWrong: (runId, because) =>
    call(`/v1/runs/${encodeURIComponent(runId)}/wrong`, { method: "POST", body: { because } }),

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

  /** This operator's running conversation, started if they have none. */
  currentThread: () => call("/v1/threads/current"),

  /** Say something into it. Answers with the whole thread, which is why the
   * panel re-renders from the reply rather than appending locally. */
  say: (threadId, text) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: { text },
    }),

  /** The press. Promotes the version a preview just showed and starts it in
   * the operator's own browser in one call -- see ADR 014 and
   * `RunFromPreview`. Refused for a looped skill with a sentence written for
   * an operator to read, which the panel shows rather than swallows.
   *
   * `version` is the one the panel rendered, and is what makes ADR 014's
   * central claim true rather than merely stated: the backend runs that
   * version and refuses the press outright where the skill has been taught
   * again since, instead of quietly running whichever version happens to be
   * newest by the time the press lands. */
  runFromPreview: (skillId, parameters, deviceId, intent, version) =>
    call(`/v1/skills/${encodeURIComponent(skillId)}/runs/from-preview`, {
      method: "POST",
      body: { parameters, device_id: deviceId, intent, version },
    }),

  /** Ask the backend to stop stepping a run it is performing in this browser.
   *
   * The other half of the Stop button. `commands.js`'s `abort` makes this
   * browser refuse every later command for the run, which is immediate and is
   * why it is still done first -- but the backend goes on stepping regardless,
   * sending each next command into a browser that answers `aborted`, so a run
   * the operator stopped kept running until it ran out of steps. Two
   * implementations of stopping, one of which the operator could not reach.
   *
   * A 409 is swallowed, and only a 409. That is the backend saying there was
   * nothing left to stop -- the run already ended, or it is not one this
   * process drives -- and pressing Stop as a run finishes is an ordinary race,
   * not a fault. Reporting it turned "your run is stopping" into "the run
   * could not be told: that run already succeeded", which is a stop control
   * raising an alarm about a run that had already stopped: louder than the
   * silence it replaced and no more true. Everything else still throws, so a
   * backend this browser genuinely cannot reach -- a run still stepping
   * somewhere with nobody able to say so -- reaches the operator who just
   * pressed Stop.
   *
   * The decision lives here rather than in the worker's message handler
   * because this file is importable on its own; `service-worker.js` registers
   * chrome listeners the moment it loads and cannot be exercised in a test. */
  stopRun: async (runId) => {
    try {
      return await call(`/v1/runs/${encodeURIComponent(runId)}/stop`, { method: "POST" });
    } catch (error) {
      if (error.status === 409) return null;
      throw error;
    }
  },

  /** Change what the steps still to come will run with.
   *
   * Only names the skill declares; the run refuses anything else rather than
   * recording a decision that reaches nothing. Answers with the run as it
   * stands, which is not the effect of the change -- the next step is a fresh
   * read and renders from what this saved. */
  reviseRun: (runId, values) =>
    call(`/v1/runs/${encodeURIComponent(runId)}/values`, {
      method: "POST",
      body: { values },
    }),

  /** Say something to a run that is happening.
   *
   * Kept beside it and resolved against nothing: an operator watching a run who
   * types "use the north yard address" is talking about the thing in front of
   * them, and putting that through intent matching finds some other skill and
   * offers to run it. */
  sayToRun: (threadId, runId, text) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: { text, run_id: runId },
    }),

  /** What this tenant has watched, noticed and done since a moment.
   *
   * The panel asks for today, to say three numbers over the ledger. Counted
   * from rows somebody can open rather than tallied in the browser: a figure a
   * person repeats to their manager has to be one an auditor can reach. */
  summary: (since) =>
    call(`/v1/analytics/summary?since=${encodeURIComponent(since)}`),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, { method: "DELETE" }),
};
