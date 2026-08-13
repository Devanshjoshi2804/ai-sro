"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { finishRecording, getLiveView, recordingKeys } from "@/features/recording/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * The browser the operator drives, embedded, plus the two ways to end it.
 *
 * The live view URL is fetched rather than carried over from the start call, so
 * a refresh mid-demonstration does not lose the session.
 */
export function LiveSession({
  recordingId,
  frameCount,
}: {
  recordingId: string;
  frameCount: number;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const liveView = useQuery({
    queryKey: [...recordingKeys.detail(recordingId), "live-view"],
    queryFn: () => getLiveView(recordingId),
    refetchInterval: 15_000,
  });

  const finish = useMutation({
    mutationFn: (reason?: string) => finishRecording(recordingId, reason),
    onSuccess: (recording) => {
      toast.success(
        recording.status === "sealed"
          ? `Sealed with ${recording.frame_count} steps`
          : "Demonstration abandoned",
      );
      void queryClient.invalidateQueries({ queryKey: recordingKeys.detail(recordingId) });
      void queryClient.invalidateQueries({ queryKey: recordingKeys.all });
      router.refresh();
    },
    onError: (error) =>
      toast.error("Could not finish", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const url = liveView.data?.live_view_url;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <span className="relative flex h-2 w-2">
            <span className="bg-destructive absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" />
            <span className="bg-destructive relative inline-flex h-2 w-2 rounded-full" />
          </span>
          Recording — {frameCount} step{frameCount === 1 ? "" : "s"} captured
        </CardTitle>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={finish.isPending}
            onClick={() => finish.mutate("abandoned by the operator")}
          >
            Abandon
          </Button>
          <Button
            disabled={finish.isPending || frameCount === 0}
            onClick={() => finish.mutate(undefined)}
            // Sealing a recording with no frames is refused by the domain; say
            // so here rather than letting the button produce a 422.
            title={frameCount === 0 ? "Do something in the browser first" : undefined}
          >
            {finish.isPending ? "Finishing…" : "Finish and seal"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {url ? (
          <>
            <iframe
              src={url}
              title="Browser session"
              className="bg-background h-[600px] w-full rounded-md border"
              // The session is the operator's own browser; it needs to run
              // scripts and set cookies for the WMS to work at all.
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
            />
            <p className="text-muted-foreground mt-2 text-xs">
              Trouble interacting here?{" "}
              <a href={url} target="_blank" rel="noreferrer" className="underline">
                Open the session in a new tab
              </a>{" "}
              — capture continues either way.
            </p>
          </>
        ) : (
          <p className="text-muted-foreground py-12 text-center text-sm">
            {liveView.isLoading
              ? "Connecting to the browser session…"
              : "No live view — the browser session has ended. Finish or abandon this recording."}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
