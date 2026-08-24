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
