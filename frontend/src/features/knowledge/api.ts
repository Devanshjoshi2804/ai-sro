import { api, type Schemas } from "@/lib/api/client";

export type KnowledgeSummary = Schemas["KnowledgeSummaryModel"];
export type KnowledgeEntry = Schemas["KnowledgeEntryModel"];
export type TaughtSkill = Schemas["TaughtSkillModel"];

export const knowledgeKeys = {
  summary: ["knowledge", "summary"] as const,
  search: (q: string) => ["knowledge", "search", q] as const,
};

export const getKnowledgeSummary = () => api.get<KnowledgeSummary>("/v1/knowledge/summary");

export const searchKnowledge = (q: string) =>
  api.get<KnowledgeEntry[]>(`/v1/knowledge?q=${encodeURIComponent(q)}&limit=40`);
