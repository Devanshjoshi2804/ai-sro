import { api, type Schemas } from "@/lib/api/client";

export type KnowledgeSummary = Schemas["KnowledgeSummaryModel"];
export type KnowledgeEntry = Schemas["KnowledgeEntryModel"];

export type OpenQuestion = Schemas["OpenQuestionModel"];

export const knowledgeKeys = {
  summary: ["knowledge", "summary"] as const,
  search: (q: string) => ["knowledge", "search", q] as const,
  questions: ["knowledge", "questions"] as const,
};

export const getKnowledgeSummary = () => api.get<KnowledgeSummary>("/v1/knowledge/summary");

export const searchKnowledge = (q: string) =>
  api.get<KnowledgeEntry[]>(`/v1/knowledge?q=${encodeURIComponent(q)}&limit=40`);

export const listOpenQuestions = () => api.get<OpenQuestion[]>("/v1/knowledge/questions");

export const answerQuestion = (question: { system: string; key: string; chosen: string }) =>
  api.post<void>("/v1/knowledge/questions/answer", question);
