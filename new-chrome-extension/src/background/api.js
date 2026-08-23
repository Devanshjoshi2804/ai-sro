// Every call to the backend. See docs/14-extension-protocol.md.

import { state } from "./state.js";

export class ApiError extends Error {
  constructor(status, problem) {
    super(problem?.detail || problem?.title || `HTTP ${status}`);
    this.status = status;
    this.problem = problem;
  }
}

async function call(path, { method = "GET", body, signal } = {}) {
  const [base, token] = await Promise.all([state.apiUrl(), state.token()]);
  const response = await fetch(`${base}${path}`, {
    method,
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
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

  policy: () => call("/v1/agents/policy"),
};
