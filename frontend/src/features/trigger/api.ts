import { api, type Schemas } from "@/lib/api/client";

export type TriggerModel = Schemas["TriggerModel"];
export type NewTriggerRequest = Schemas["NewTriggerRequest"];
export type SkillSummary = Schemas["SkillSummary"];

export const triggerKeys = {
  all: ["triggers"] as const,
};

export const listTriggers = () => api.get<TriggerModel[]>("/v1/triggers");

export const createTrigger = (body: NewTriggerRequest) =>
  api.post<TriggerModel>("/v1/triggers", body);

export const setTriggerEnabled = (id: string, enabled: boolean, reason = "") =>
  api.patch<TriggerModel>(`/v1/triggers/${id}`, { enabled, reason });

export const fireTrigger = (id: string) => api.post(`/v1/triggers/${id}/fire`, {});
