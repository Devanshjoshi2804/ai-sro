import { api, type Schemas } from "@/lib/api/client";

export type TriggerModel = Schemas["TriggerModel"];
export type NewTriggerRequest = Schemas["NewTriggerRequest"];
export type SkillSummary = Schemas["SkillSummary"];

export const triggerKeys = {
  all: ["triggers"] as const,
};

export type DeviceModel = Schemas["DeviceModel"];

export const deviceKeys = { all: ["devices"] as const };

/** The browsers this tenant has registered. A trigger that may take somebody's
 * screen has to name one: without a device the run happens server-side, where
 * there is no screen to take. */
export const listDevices = () => api.get<DeviceModel[]>("/v1/agents");

export const listTriggers = () => api.get<TriggerModel[]>("/v1/triggers");

export const createTrigger = (body: NewTriggerRequest) =>
  api.post<TriggerModel>("/v1/triggers", body);

export const setTriggerEnabled = (id: string, enabled: boolean, reason = "") =>
  api.patch<TriggerModel>(`/v1/triggers/${id}`, { enabled, reason });

export const fireTrigger = (id: string) => api.post(`/v1/triggers/${id}/fire`, {});

export type Confirmation = Schemas["ConfirmationModel"];
export type Answered = Schemas["AnsweredModel"];

export const confirmationKeys = {
  all: ["confirmations"] as const,
};

/**
 * Fires waiting for somebody to say yes.
 *
 * A manual trigger needs none of this — the click that fires it is the
 * confirmation. A schedule and an inbound message both go off with nobody
 * there, and this is where those wait.
 */
export const listConfirmations = () => api.get<Confirmation[]>("/v1/confirmations");

/** Yes — and the run starts here, with this person's name on it. */
export const approveConfirmation = (id: string) =>
  api.post<Answered>(`/v1/confirmations/${id}/approve`, {});

export const declineConfirmation = (id: string, note: string) =>
  api.post<Answered>(`/v1/confirmations/${id}/decline`, { note });
