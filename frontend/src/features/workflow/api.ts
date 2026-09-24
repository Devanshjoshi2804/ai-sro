import { api, type Schemas } from "@/lib/api/client";

export type WorkflowModel = Schemas["WorkflowModel"];
export type WorkflowStepModel = Schemas["WorkflowStepModel"];
export type WorkflowRunModel = Schemas["WorkflowRunModel"];
export type WorkflowRunStepModel = Schemas["WorkflowRunStepModel"];
export type DeviceLineModel = Schemas["DeviceLineModel"];

export type EvidenceResponse = Schemas["EvidenceResponse"];

export const workflowKeys = {
  all: ["workflows"] as const,
  evidence: (workflowId: string) => ["workflows", workflowId, "evidence"] as const,
};

export const workflowRunKeys = {
  all: ["workflow-runs"] as const,
  awaiting: ["workflow-runs", "awaiting"] as const,
  of: (workflowId: string) => ["workflow-runs", "of", workflowId] as const,
  detail: (runId: string) => ["workflow-runs", runId] as const,
};

export const rosterKeys = { all: ["roster"] as const };

export const listWorkflows = () =>
  api.get<{ workflows: WorkflowModel[] }>("/v1/workflows").then((r) => r.workflows);

/**
 * What a mined job was mined FROM: the gestures its steps cite, the calls
 * those gestures carried, the recordings they came from, and -- the point of
 * the route -- the cited ids that are no longer there.
 *
 * `missing` is not an error field. Evidence ages out of the pool, and a step
 * whose citations have gone is a step nobody can check any more. It is the one
 * thing on this page that gets louder rather than quieter over time.
 */
export const readEvidence = (workflowId: string) =>
  api.get<EvidenceResponse>(`/v1/workflows/${encodeURIComponent(workflowId)}/evidence`);

export const listRunsOfWorkflow = (workflowId: string) =>
  api.get<WorkflowRunModel[]>(
    `/v1/workflow-runs?workflow_id=${encodeURIComponent(workflowId)}&limit=10`,
  );

export const getWorkflowRun = (runId: string) =>
  api.get<WorkflowRunModel>(`/v1/workflow-runs/${encodeURIComponent(runId)}`);

/**
 * `started_by` is deliberately absent: the route reads the starter off the
 * credential. The rig sent `started_by: "form"` and the backend refuses to
 * take a name nobody checked.
 */
export const startWorkflowRun = (body: {
  workflow_id: string;
  device_id: string;
  values: Record<string, string>;
  live: boolean;
}) => api.post<WorkflowRunModel>("/v1/workflow-runs", { ...body, allow_focus: true });

/** A bare POST. A body here would be a name nobody checked.
 *
 * `resumed` is the field worth reading: false means the write was authorised
 * and nothing is holding the run, so the browser will not move. */
export const approveWorkflowRun = (runId: string) =>
  api.post<{ order: number; first: boolean; resumed: boolean }>(
    `/v1/workflow-runs/${encodeURIComponent(runId)}/approve`,
  );

export const abortWorkflowRun = (runId: string) =>
  api.post<WorkflowRunModel>(`/v1/workflow-runs/${encodeURIComponent(runId)}/abort`);

export const listBrowsers = () =>
  api.get<{ devices: DeviceLineModel[] }>("/v1/devices").then((r) => r.devices);
