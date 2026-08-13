import { api, type Schemas } from "@/lib/api/client";

export type RecordingSummary = Schemas["RecordingSummary"];
export type RecordingDetail = Schemas["RecordingDetail"];
export type StartRecordingRequest = Schemas["StartRecordingRequest"];
export type StartRecordingResponse = Schemas["StartRecordingResponse"];
export type FrameSummary = Schemas["FrameSummary"];

export const recordingKeys = {
  all: ["recordings"] as const,
  detail: (id: string) => ["recordings", id] as const,
};

export const listRecordings = () => api.get<RecordingSummary[]>("/v1/recordings");

export const getRecording = (id: string) => api.get<RecordingDetail>(`/v1/recordings/${id}`);

export const startRecording = (body: StartRecordingRequest) =>
  api.post<StartRecordingResponse>("/v1/recordings", body);

export type Media = Schemas["MediaModel"];

export const getMedia = (id: string) => api.get<Media[]>(`/v1/recordings/${id}/media`);

export const getLiveView = (id: string) =>
  api.get<{ live_view_url: string | null }>(`/v1/recordings/${id}/live-view`);

export const finishRecording = (id: string, abandonReason?: string) =>
  api.post<RecordingSummary>(`/v1/recordings/${id}/finish`, {
    abandon_reason: abandonReason ?? null,
  });
