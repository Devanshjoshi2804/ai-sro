"use client";

import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { getMedia, recordingKeys, type FrameSummary } from "@/features/recording/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The demonstration as the operator saw it, with the steps as chapter marks.
 *
 * The value is in the pairing: a reviewer reads "step 2 released the wave" and
 * wants to see what was on screen when it happened, without scrubbing for it.
 */
export function RecordingVideo({
  recordingId,
  frames,
  startedAt,
}: {
  recordingId: string;
  frames: FrameSummary[];
  startedAt: string;
}) {
  const player = useRef<HTMLVideoElement>(null);

  const media = useQuery({
    queryKey: [...recordingKeys.detail(recordingId), "media"],
    queryFn: () => getMedia(recordingId),
  });

  if (media.isLoading) return <Skeleton className="h-96 w-full" />;

  const video = media.data?.find((item) => item.kind === "video");
  if (!video) {
    return (
      <p className="text-muted-foreground py-12 text-center text-sm">
        No video for this recording. Capture may have been running with video disabled.
      </p>
    );
  }

  // The video starts at the first repaint, not at the recording's first
  // millisecond, so offsets are measured from frame zero rather than from
  // startedAt when a frame exists.
  const origin = frames.length ? Date.parse(frames[0].occurred_at) : Date.parse(startedAt);
  const seek = (occurredAt: string) => {
    const seconds = Math.max(0, (Date.parse(occurredAt) - origin) / 1000);
    if (player.current) {
      player.current.currentTime = seconds;
      void player.current.play();
    }
  };

  return (
    <div className="space-y-4">
      <video
        ref={player}
        src={video.url}
        controls
        preload="metadata"
        // A browser window is taller than it is wide once scaled to the page
        // width; cap it so the step markers stay reachable without scrolling.
        className="bg-muted max-h-[65vh] w-full rounded-md border object-contain"
      />

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground text-sm">Jump to step:</span>
        {frames.map((frame) => (
          <Button
            key={frame.index}
            variant="outline"
            size="sm"
            onClick={() => seek(frame.occurred_at)}
          >
            #{frame.index} {frame.action_kind}
            {frame.target ? ` · ${frame.target}` : ""}
          </Button>
        ))}
        {frames.length === 0 && (
          <span className="text-muted-foreground text-sm">No steps were captured.</span>
        )}
      </div>

      <p className="text-muted-foreground text-xs">
        <Badge variant="secondary" className="mr-2">
          {Math.round(video.size_bytes / 1024)} KB
        </Badge>
        {video.duration_ms ? `${(video.duration_ms / 1000).toFixed(1)}s · ` : ""}
        Link expires in 30 minutes.
      </p>
    </div>
  );
}
