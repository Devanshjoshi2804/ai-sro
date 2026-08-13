import { api, type Schemas } from "@/lib/api/client";

export type SkillSummary = Schemas["SkillSummary"];
export type SkillDetail = Schemas["SkillDetail"];
export type SkillVersionModel = Schemas["SkillVersionModel"];
export type StepModel = Schemas["StepModel"];
export type ParameterModel = Schemas["ParameterModel"];
export type InductionResponse = Schemas["InductionResponse"];

export const skillKeys = {
  all: ["skills"] as const,
  detail: (id: string) => ["skills", id] as const,
};

export const listSkills = () => api.get<SkillSummary[]>("/v1/skills");

export const getSkill = (id: string) => api.get<SkillDetail>(`/v1/skills/${id}`);

export const induceSkill = (firstRecordingId: string, secondRecordingId: string, name?: string) =>
  api.post<InductionResponse>("/v1/skills/induct", {
    first_recording_id: firstRecordingId,
    second_recording_id: secondRecordingId,
    name: name ?? null,
  });

/** v0 permits `recorded → shadow` only; the backend refuses anything further. */
export const promoteSkill = (skillId: string, version: number, to: string) =>
  api.post<SkillVersionModel>(`/v1/skills/${skillId}/promote`, { version, to });
