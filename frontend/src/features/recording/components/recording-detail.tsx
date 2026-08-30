"use client";

import { useQuery } from "@tanstack/react-query";
import { getMedia, getRecording, recordingKeys } from "@/features/recording/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FrameShot, shotsByFrame } from "@/features/recording/components/frame-shot";
import { LiveSession } from "@/features/recording/components/live-session";
import { RecordingVideo } from "@/features/recording/components/recording-video";

export function RecordingDetail({ recordingId }: { recordingId: string }) {
  const recording = useQuery({
    queryKey: recordingKeys.detail(recordingId),
    queryFn: () => getRecording(recordingId),
    // Frames arrive on the capture drain interval, so an open recording is
    // polled; a finished one never changes again.
    refetchInterval: (query) => (query.state.data?.status === "capturing" ? 5_000 : false),
  });

  // Links are minted per request and expire, so they are fetched beside the
  // recording rather than stored with it.
  const media = useQuery({
    queryKey: [...recordingKeys.detail(recordingId), "media"],
    queryFn: () => getMedia(recordingId),
  });

  if (recording.isLoading) return <Skeleton className="h-96 w-full" />;
  if (recording.error) return <p className="text-destructive">{String(recording.error)}</p>;
  if (!recording.data) return null;

  const { objective_key: objective, frames, artifacts } = recording.data;
  const shots = shotsByFrame(media.data);

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          {objective?.objective_type ?? "Unnamed run"}{" "}
          <span className="text-muted-foreground">
            · {recording.data.label ?? recording.data.id}
          </span>
        </h1>
        <p className="text-muted-foreground text-sm">
          {objective
            ? `${objective.target_system} · ${objective.facility} · ${objective.entity_type} · ${objective.direction}`
            : "still capturing — the evidence names the task when it is sealed"}{" "}
          — demonstrated by {recording.data.demonstrator}
        </p>
      </header>

      {recording.data.status === "capturing" && (
        <LiveSession recordingId={recordingId} frameCount={frames.length} />
      )}

      <Tabs defaultValue="frames">
        <TabsList>
          <TabsTrigger value="frames">Timeline ({frames.length})</TabsTrigger>
          <TabsTrigger value="video">Video</TabsTrigger>
          <TabsTrigger value="artifacts">Artifacts ({artifacts.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="frames" className="space-y-3 pt-4">
          {frames.map((frame) => (
            <Card key={frame.index}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-3 text-base">
                  <span className="text-muted-foreground tabular-nums">#{frame.index}</span>
                  <Badge variant="outline">{frame.action_kind}</Badge>
                  <span className="font-normal">{frame.target ?? "—"}</span>
                  {frame.error_count > 0 && (
                    <Badge variant="destructive">{frame.error_count} errors</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex gap-4 text-sm">
                <FrameShot
                  shot={shots.get(frame.index)}
                  label={`#${frame.index} ${frame.action_kind} ${frame.target ?? ""}`.trim()}
                />
                <div className="text-muted-foreground space-y-1">
                  <p>{new Date(frame.occurred_at).toLocaleTimeString()}</p>
                  {frame.primary_request && (
                    <p className="text-foreground font-mono text-xs break-all">
                      {frame.primary_request}
                    </p>
                  )}
                  <p>{frame.request_count} network calls captured</p>
                </div>
              </CardContent>
            </Card>
          ))}
          {frames.length === 0 && (
            <p className="text-muted-foreground py-12 text-center">No frames captured.</p>
          )}
        </TabsContent>

        <TabsContent value="video" className="pt-4">
          <RecordingVideo
            recordingId={recordingId}
            frames={frames}
            startedAt={recording.data.started_at}
          />
        </TabsContent>

        <TabsContent value="artifacts" className="pt-4">
          {/* Contact sheet rather than a list of keys: an artifact is a picture
              of somebody's screen, and a URI is not a way to look at one. */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {artifacts.map((artifact) => {
              const shot =
                artifact.frame_index !== null ? shots.get(artifact.frame_index) : undefined;
              return (
                <div key={`${artifact.kind}-${artifact.uri}`} className="space-y-1">
                  {shot ? (
                    <FrameShot shot={shot} label={`#${artifact.frame_index} of this doing`} />
                  ) : (
                    <span className="text-muted-foreground block truncate font-mono text-xs">
                      {artifact.uri}
                    </span>
                  )}
                  <p className="text-muted-foreground flex items-center gap-2 text-xs">
                    <Badge variant="secondary">{artifact.kind}</Badge>
                    {artifact.frame_index !== null && (
                      <span className="tabular-nums">#{artifact.frame_index}</span>
                    )}
                    <span className="tabular-nums">
                      {Math.round(artifact.size_bytes / 1024)} KB
                    </span>
                  </p>
                </div>
              );
            })}
          </div>
          {artifacts.length === 0 && (
            <p className="text-muted-foreground py-12 text-center">No artifacts attached.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
