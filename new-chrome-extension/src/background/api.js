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

  /** Start a demonstration this browser will fill. Nothing is opened on the
   * server: the operator is already in front of the system. */
  startRecording: (deviceId, label) =>
    call("/v1/recordings", { method: "POST", body: { device_id: deviceId, label } }),

  /** Seal it. The backend assembles the frames from what this browser
   * uploaded, so everything must have gone up before this is called. */
  finishRecording: (recordingId) =>
    call(`/v1/recordings/${encodeURIComponent(recordingId)}/finish`, {
      method: "POST",
      body: {},
    }),

  /** The operator deleting their own evidence, from their own devices, for the
   * tenant on their credential. Answers with what went. */
  forget: (since) =>
    call(`/v1/observations?since=${encodeURIComponent(since)}`, { method: "DELETE" }),
};
