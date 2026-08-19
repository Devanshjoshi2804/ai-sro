import { api, type Schemas } from "@/lib/api/client";

export type SkillSummary = Schemas["SkillSummary"];
export type SkillDetail = Schemas["SkillDetail"];
export type SkillVersionModel = Schemas["SkillVersionModel"];
export type StepModel = Schemas["StepModel"];
export type ParameterModel = Schemas["ParameterModel"];
export type InductionResponse = Schemas["InductionResponse"];

export type Choice = Schemas["ChoiceModel"];

export const skillKeys = {
  all: ["skills"] as const,
  detail: (id: string) => ["skills", id] as const,
  choices: (id: string, parameter: string, q: string) =>
    ["skills", id, "choices", parameter, q] as const,
};

export const listSkills = () => api.get<SkillSummary[]>("/v1/skills");

export const getSkill = (id: string) => api.get<SkillDetail>(`/v1/skills/${id}`);

/**
 * Two demonstrations, or one.
 *
 * Without a second recording there is nothing to diff, so the skill keeps every
 * value exactly as it was demonstrated and takes no parameters. That is the
 * trade the operator is making, not a degraded mode to hide.
 */
export const induceSkill = (
  firstRecordingId: string,
  secondRecordingId?: string | null,
  name?: string,
) =>
  api.post<InductionResponse>("/v1/skills/induct", {
    first_recording_id: firstRecordingId,
    second_recording_id: secondRecordingId ?? null,
    name: name ?? null,
  });

export const promoteSkill = (
  skillId: string,
  version: number,
  to: string,
  acknowledgingFixedValues = false,
) =>
  api.post<SkillVersionModel>(`/v1/skills/${skillId}/promote`, {
    version,
    to,
    // Only ever true because somebody was shown what the version sends and
    // said so. A default of true here would turn the one refusal a supervisor
    // is asked to answer into a refusal nobody ever sees.
    acknowledging_fixed_values: acknowledgingFixedValues,
  });

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
  api.get<Choice[]>(
    `/v1/skills/${skillId}/choices/${parameter}?q=${encodeURIComponent(q)}`,
  );
