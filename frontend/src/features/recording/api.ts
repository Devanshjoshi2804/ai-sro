import { api, type Schemas } from "@/lib/api/client";

export type RecordingSummary = Schemas["RecordingSummary"];
export type RecordingDetail = Schemas["RecordingDetail"];
export type StartRecordingRequest = Schemas["StartRecordingRequest"];
export type StartRecordingResponse = Schemas["StartRecordingResponse"];
export type FrameSummary = Schemas["FrameSummary"];
export type ObjectiveKey = Schemas["ObjectiveKeyModel"];

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

/** Narration audio, with the moment the microphone started so a transcript's
 * offsets can be lined up against the frames. */
export const attachNarration = (id: string, audio: Blob, recordedFrom: Date) => {
  const form = new FormData();
  form.append("kind", "audio");
  form.append("file", audio, "narration.webm");
  form.append("recorded_from", recordedFrom.toISOString());
  return api.upload<{ kind: string; uri: string }>(`/v1/recordings/${id}/artifacts`, form);
};

export const finishRecording = (
  id: string,
  abandonReason?: string,
  objectiveKey?: ObjectiveKey | null,
) =>
  api.post<RecordingSummary>(`/v1/recordings/${id}/finish`, {
    abandon_reason: abandonReason ?? null,
    // Only the second run of a pair carries one: the first names itself from
    // what it did, and both runs must end up under the same name to pair.
    objective_key: objectiveKey ?? null,
  });
