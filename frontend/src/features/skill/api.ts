import { api, type Schemas } from "@/lib/api/client";

export type SkillSummary = Schemas["SkillSummary"];
export type SkillDetail = Schemas["SkillDetail"];
export type SkillVersionModel = Schemas["SkillVersionModel"];
export type TrackRecordModel = Schemas["TrackRecordModel"];
export type StepModel = Schemas["StepModel"];
export type ParameterModel = Schemas["ParameterModel"];

export type Choice = Schemas["ChoiceModel"];
export type AssertionModel = Schemas["AssertionModel"];

export const skillKeys = {
  all: ["skills"] as const,
  detail: (id: string) => ["skills", id] as const,
  choices: (id: string, parameter: string, q: string) =>
    ["skills", id, "choices", parameter, q] as const,
};

export const listSkills = () => api.get<SkillSummary[]>("/v1/skills");

export const getSkill = (id: string) => api.get<SkillDetail>(`/v1/skills/${id}`);

/** Rewords what the skill is found by. Never what it does. */
export const describeSkill = (
  skillId: string,
  version: number,
  summary: string,
  whenToUse: string,
) =>
  api.post<SkillVersionModel>(`/v1/skills/${skillId}/describe`, {
    version,
    summary,
    when_to_use: whenToUse,
  });

/**
 * What a field's dropdown holds, from the target system, now.
 *
 * The field was a dropdown when the task was taught — a supplier's address is
 * picked, never typed — so it stays one, and the options come from the same
 * endpoint the screen used rather than from what was recorded that afternoon.
 */
export const listChoices = (skillId: string, parameter: string, q: string) =>
  api.get<Choice[]>(`/v1/skills/${skillId}/choices/${parameter}?q=${encodeURIComponent(q)}`);
