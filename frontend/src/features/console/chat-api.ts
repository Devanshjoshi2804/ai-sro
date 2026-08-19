import { api, type Schemas } from "@/lib/api/client";

export type ThreadSummary = Schemas["ThreadSummary"];
export type ThreadDetail = Schemas["ThreadDetail"];
export type ChatMessage = Schemas["MessageModel"];

export const threadKeys = {
  all: ["threads"] as const,
  detail: (id: string) => ["threads", id] as const,
};

export const listThreads = () => api.get<ThreadSummary[]>("/v1/threads");

export const getThread = (id: string) => api.get<ThreadDetail>(`/v1/threads/${id}`);

export const startThread = () => api.post<ThreadDetail>("/v1/threads");

/** Says something and gets the whole thread back, decision included. Starting a
 * run is a separate request — the reply is an offer, not an action. */
export const say = (threadId: string, text: string, parameters?: Record<string, string>) =>
  api.post<ThreadDetail>(`/v1/threads/${threadId}/messages`, {
    text,
    system: null,
    parameters: parameters ?? {},
  });

/**
 * Start a run and keep it in the conversation that asked for it.
 *
 * The same run as `/v1/skills/{id}/runs`, recorded as a message: a result held
 * only in component state was gone on the next render and on every reload, so
 * a card that had just created a supplier came back as an empty form.
 */
export const runInThread = (
  threadId: string,
  skillId: string,
  parameters: Record<string, string>,
  options: { version?: number; authorized?: boolean } = {},
) =>
  api.post<ThreadDetail>(`/v1/threads/${threadId}/runs`, {
    skill_id: skillId,
    parameters,
    version: options.version ?? null,
    authorized_by: options.authorized === false ? null : "confirmed",
    medium: "network",
  });

export type Pursuit = Schemas["PursuitProgressModel"];

/**
 * Work a task out on the screen, when nobody has demonstrated it.
 *
 * Accepted, not performed: a pursuit is a dozen gestures, each a screenshot to
 * a model and back. What comes back is something to watch.
 */
export const pursue = (
  threadId: string,
  intent: string,
  targetSystem: string,
  values: Record<string, string> = {},
) =>
  api.post<Pursuit>(`/v1/threads/${threadId}/pursue`, {
    intent,
    target_system: targetSystem,
    values,
  });

export const pursuitProgress = (threadId: string, pursuitId: string) =>
  api.get<Pursuit>(`/v1/threads/${threadId}/pursue/${pursuitId}`);
