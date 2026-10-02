import { api, type Schemas } from "@/lib/api/client";

export type Integration = Schemas["IntegrationModel"];
export type ConnectSession = Schemas["ConnectSessionModel"];

export const integrationKeys = { all: ["integrations"] as const };

export const listIntegrations = () => api.get<Integration[]>("/v1/integrations");

export const createConnectSession = (integration: string) =>
  api.post<ConnectSession>("/v1/integrations/connect-session", { integration });

const NAMES: Record<string, string> = {
  microsoft: "Outlook",
  slack: "Slack",
  "google-mail": "Gmail",
  gmail: "Gmail",
};

export const displayName = (integration: string) => NAMES[integration] ?? integration;
