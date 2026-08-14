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
