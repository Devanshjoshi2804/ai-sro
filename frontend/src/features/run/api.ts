import { api, type Schemas } from "@/lib/api/client";

export type RunModel = Schemas["RunModel"];
export type StepOutcomeModel = Schemas["StepOutcomeModel"];

export const runKeys = {
  all: ["runs"] as const,
  detail: (id: string) => ["runs", id] as const,
};

export const listRuns = () => api.get<RunModel[]>("/v1/runs");

export const getRun = (id: string) => api.get<RunModel>(`/v1/runs/${id}`);

/**
 * Ask a run in your own browser to stop.
 *
 * Accepted rather than done: it takes effect at the run's next step, because a
 * gesture already sent cannot be recalled from a warehouse. Refused with a 409
 * for a run the deployment is performing on its own — answering "stopping" for
 * a run that will finish anyway is the one thing a stop control must not do.
 */
export const stopRun = (id: string) => api.post<RunModel>(`/v1/runs/${id}/stop`, {});

/**
 * Starts a run. `authorizedBy` is the operator confirming — above shadow the
 * backend refuses a run that names nobody, because a run that changed a
 * warehouse has to say who allowed it.
 */
export const startRun = (
  skillId: string,
  parameters: Record<string, string>,
  options: {
    authorizedBy?: string;
    medium?: "network" | "ui" | "vision";
    version?: number;
    /** Whose browser it goes out of. A skill that touches two systems has no
     * other way to run: the deployment holds one system's credentials at most,
     * and the operator's own Chrome is signed in to both. */
    deviceId?: string | null;
    /** Whether this run may bring a tab to the front.
     *
     * True when a person pressed the button and is watching it happen, which is
     * what the flag is for -- and it is why `focus_not_permitted` should be a
     * state the console almost never has to draw. Left alone for a schedule
     * firing behind somebody at three in the afternoon. */
    mayTakeFocus?: boolean;
  } = {},
) =>
  api.post<RunModel>(`/v1/skills/${skillId}/runs`, {
    parameters,
    authorized_by: options.authorizedBy ?? null,
    medium: options.medium ?? "network",
    version: options.version ?? null,
    device_id: options.deviceId ?? null,
    may_take_focus: options.mayTakeFocus ?? false,
  });

export type BatchResult = Schemas["BatchResultModel"];
export type BatchItem = Schemas["BatchItemModel"];

/**
 * Runs one taught skill against several parameter sets. The operator confirmed
 * the table; that confirmation is the authorisation each assisted run records.
 */
export const runBatch = (
  skillId: string,
  items: Record<string, string>[],
  options: { authorizedBy?: string; version?: number; medium?: string } = {},
) =>
  api.post<BatchResult>(`/v1/skills/${skillId}/batch`, {
    items,
    authorized_by: options.authorizedBy ?? null,
    version: options.version ?? null,
    medium: options.medium ?? "network",
  });
