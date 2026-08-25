import { api, type Schemas } from "@/lib/api/client";

export type TaskCandidateModel = Schemas["TaskCandidateModel"];
export type TaughtModel = Schemas["TaughtModel"];

export const candidateKeys = {
  all: (seenAtLeast: number) => ["candidates", seenAtLeast] as const,
};

export const listCandidates = (seenAtLeast = 3) =>
  api.get<TaskCandidateModel[]>(`/v1/candidates?seen_at_least=${seenAtLeast}`);

export const teachCandidate = (id: string) =>
  api.post<TaughtModel>(`/v1/candidates/${id}/teach`, {});

export const dismissCandidate = (id: string, reason: string) =>
  api.post<TaskCandidateModel>(`/v1/candidates/${id}/dismiss`, { reason });

export type TaughtTogetherModel = Schemas["TaughtTogetherModel"];
export type JoinModel = NonNullable<TaskCandidateModel["joins"]>[number];

/** What a person says two candidates are to each other. A model may only ever
 * have suggested it. */
export const answerJoin = (
  id: string,
  otherId: string,
  kind: JoinModel["kind"],
  answer: "same" | "different",
) => api.post<TaskCandidateModel>(`/v1/candidates/${id}/joins`, {
  other_id: otherId,
  kind,
  answer,
});

/** Two candidates a person has said are one job, taught as one skill. */
export const teachTogether = (id: string, otherId: string) =>
  api.post<TaughtTogetherModel>(`/v1/candidates/${id}/teach-together`, { other_id: otherId });
