import { api, type Schemas } from "@/lib/api/client";

export type SkillSummary = Schemas["SkillSummary"];
export type SkillDetail = Schemas["SkillDetail"];
export type SkillVersionModel = Schemas["SkillVersionModel"];
export type TrackRecordModel = Schemas["TrackRecordModel"];
export type StepModel = Schemas["StepModel"];
export type ParameterModel = Schemas["ParameterModel"];
export type InductionResponse = Schemas["InductionResponse"];

export type Choice = Schemas["ChoiceModel"];
export type Demonstration = Schemas["DemonstrationModel"];
export type ToolOffered = Schemas["ToolOfferedModel"];
export type MapStepRequest = Schemas["MapStepRequest"];

export const skillKeys = {
  all: ["skills"] as const,
  detail: (id: string) => ["skills", id] as const,
  choices: (id: string, parameter: string, q: string) =>
    ["skills", id, "choices", parameter, q] as const,
  doings: (id: string, version: number) => ["skills", id, "doings", version] as const,
  tools: (server: string) => ["skills", "tools", server] as const,
};

export const listSkills = () => api.get<SkillSummary[]>("/v1/skills");

export const getSkill = (id: string) => api.get<SkillDetail>(`/v1/skills/${id}`);

/**
 * Every demonstration a version was learned from, and what each one filled in.
 *
 * The version itself stores the values of the two doings it diffed; the rest
 * are read back out of their own recorded traffic, so a task demonstrated ten
 * times answers for all ten.
 */
export const getDoings = (id: string, version: number) =>
  api.get<Demonstration[]>(`/v1/skills/${id}/doings?version=${version}`);

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
  api.get<Choice[]>(`/v1/skills/${skillId}/choices/${parameter}?q=${encodeURIComponent(q)}`);

/** What a connector says it has, now.
 *
 * Asked so somebody mapping a step is choosing from what the server actually
 * offers rather than typing a name and finding out the first time the skill
 * fires.
 */
export const listOfferedTools = (server: string) =>
  api.get<ToolOffered[]>(`/v1/skills/tools/${encodeURIComponent(server)}`);

/**
 * Somebody saying: this click is that tool.
 *
 * The one part of a skill nobody demonstrates, so it is a decision with a name
 * on it. Answers with the whole skill because it produces a new version, and
 * the screen has to redraw around it.
 */
export const mapStepToTool = (skillId: string, body: MapStepRequest) =>
  api.post<SkillDetail>(`/v1/skills/${skillId}/steps/tool`, body);
