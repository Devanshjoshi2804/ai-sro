import { api, type Schemas } from "@/lib/api/client";

export type SummaryModel = Schemas["SummaryModel"];
export type TaskLineModel = Schemas["TaskLineModel"];

export const summaryKeys = {
  all: ["summary"] as const,
  window: (days: number) => ["summary", days] as const,
};

/** A week by default, because a week is the unit a shift pattern repeats in. */
export const getSummary = (days = 7) => api.get<SummaryModel>(`/v1/analytics/summary?days=${days}`);
