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
 * Starts a run. `authorizedBy` is the operator confirming — above shadow the
 * backend refuses a run that names nobody, because a run that changed a
 * warehouse has to say who allowed it.
 */
export const startRun = (
  skillId: string,
  parameters: Record<string, string>,
  options: { authorizedBy?: string; medium?: "network" | "ui" | "vision"; version?: number } = {},
) =>
  api.post<RunModel>(`/v1/skills/${skillId}/runs`, {
    parameters,
    authorized_by: options.authorizedBy ?? null,
    medium: options.medium ?? "network",
    version: options.version ?? null,
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
