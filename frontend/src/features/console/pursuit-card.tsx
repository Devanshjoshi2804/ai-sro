"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { pursue, pursuitProgress, threadKeys, type Pursuit } from "@/features/console/chat-api";
import { ApiError } from "@/lib/api/client";
import { LiveScreen } from "@/features/console/live-screen";
import { ink, mono } from "@/features/console/theme";

/**
 * Working a task out on the screen, where somebody can watch it happen.
 *
 * This is what the system does when nothing has been taught: read the
 * knowledge base for the screen that does it, then drive that screen and say
 * what it is doing as it does it. Twelve gestures is a minute or two of a
 * browser nobody can see, and a spinner over that is indistinguishable from a
 * hang — so every gesture appears as it happens, and there is a link to the
 * window itself.
 *
 * It is offered, never taken: driving somebody's warehouse screens is theirs
 * to authorise, and the button is that authorisation.
 */
export function PursuitCard({
  threadId,
  intent,
  system,
}: {
  threadId: string;
  intent: string;
  system: string;
}) {
  const client = useQueryClient();
  const [pursuitId, setPursuitId] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: () => pursue(threadId, intent, system),
    onSuccess: (started) => setPursuitId(started.id),
    onError: (error) =>
      toast.error("It could not start", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const progress = useQuery({
    queryKey: ["pursuit", threadId, pursuitId],
    queryFn: () => pursuitProgress(threadId, pursuitId as string),
    enabled: pursuitId !== null,
    // While it is working: often enough that gestures appear as they happen.
    refetchInterval: (query) =>
      (query.state.data?.state ?? "working") === "working" ? 1200 : false,
  });

  const live = progress.data;
  useEffect(() => {
    if (live && live.state !== "working") {
      // What it did is written into the thread by the backend; this makes the
      // conversation show it without a reload.
      void client.invalidateQueries({ queryKey: threadKeys.all });
    }
  }, [live, client]);

  if (!pursuitId) {
    return (
      <button
        onClick={() => start.mutate()}
        disabled={start.isPending}
        style={{
          alignSelf: "flex-start",
          padding: "8px 14px",
          borderRadius: 8,
          border: "none",
          background: ink.accent,
          color: "#fff",
          fontSize: 12.5,
          fontWeight: 700,
          cursor: start.isPending ? "wait" : "pointer",
        }}
      >
        {start.isPending ? "Opening a browser…" : "Work it out on the screen"}
      </button>
    );
  }

  return <Progress live={live} />;
}

function Progress({ live }: { live: Pursuit | undefined }) {
  const pursuit = live;
  const gestures = pursuit?.gestures ?? [];
  const working = (pursuit?.state ?? "working") === "working";
  // The pursuit already says which browser it took; nothing has to be matched
  // up against the provider's list, and the screen is this session's own rather
  // than whichever one the provider's single viewer happens to be showing.
  const watching = pursuit?.session_id;

  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 10,
        overflow: "hidden",
        background: ink.panel,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 9,
          padding: "10px 14px",
          borderBottom: `1px solid ${ink.lineSoft}`,
          background: working ? ink.accentWash : ink.page,
        }}
      >
        <Dot working={working} />
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>
          {working
            ? "Working it out on the screen"
            : pursuit?.state === "reached"
              ? "Done on the screen"
              : "Stopped"}
        </span>
        <span style={{ flex: 1 }} />
      </div>

      {/* Open while it works, because a gesture list says something is
          happening and only the screen says what. */}
      {watching && working && (
        <div style={{ padding: "10px 14px 0" }}>
          <LiveScreen sessionId={watching} height={360} />
        </div>
      )}

      {/* Every gesture as it happens. A list that grows is the difference
          between "it is doing something" and "it has hung". */}
      <ol style={{ margin: 0, padding: "10px 14px 12px 30px", display: "grid", gap: 5 }}>
        {gestures.map((gesture, index) => (
          <li
            key={`${index}-${gesture}`}
            style={{
              fontSize: 12,
              color: index === gestures.length - 1 && working ? ink.text : ink.textSoft,
              fontFamily: mono,
              animation: "sro-step-in 240ms ease-out",
            }}
          >
            {gesture}
          </li>
        ))}
        {gestures.length === 0 && (
          <li style={{ fontSize: 12, color: ink.textMuted }}>
            Reading what is known about this screen…
          </li>
        )}
      </ol>

      {!working && pursuit?.detail && (
        <div
          style={{
            padding: "9px 14px",
            borderTop: `1px solid ${ink.lineSoft}`,
            fontSize: 12,
            color: ink.textSoft,
          }}
        >
          {pursuit.detail}
        </div>
      )}

      <style>{`
        @keyframes sro-step-in {
          from { opacity: 0; transform: translateY(-2px); }
          to { opacity: 1; transform: none; }
        }
        @keyframes sro-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }
        @media (prefers-reduced-motion: reduce) {
          li { animation: none !important; }
        }
      `}</style>
    </div>
  );
}

function Dot({ working }: { working: boolean }) {
  return (
    <span
      style={{
        width: 8,
        height: 8,
        borderRadius: 999,
        background: working ? ink.accent : ink.goodDot,
        animation: working ? "sro-pulse 1.1s ease-in-out infinite" : undefined,
      }}
    />
  );
}
