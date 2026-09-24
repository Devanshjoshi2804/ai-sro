import { api, type Schemas } from "@/lib/api/client";

export type Connection = Schemas["ConnectionModel"];

export const connectionKeys = {
  all: ["connections"] as const,
};

export const listConnections = () => api.get<Connection[]>("/v1/connections");
