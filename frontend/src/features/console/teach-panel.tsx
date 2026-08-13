"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  finishRecording,
  getLiveView,
  getRecording,
  recordingKeys,
  type FrameSummary,
} from "@/features/recording/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * A teaching session: a live browser, captured from the moment it opens.
 *
 * There is no record button, because the session *is* the recording — an
 * operator who has to remember to press record produces recordings that start
 * three clicks late.
 *
 * There is no seal button either. The demonstration announces its own ending:
 * when the system under test accepts a mutating call, the work happened, and
 * the response says so. That is detected rather than asked about.
 *
 * What is not automatic is the moment of sealing. A task can apply several
 * things — adjust, then confirm, then print — and sealing is irreversible, so a
 * run sealed at the first 200 is a demonstration missing its last steps. The
 * first accepted mutation therefore starts a short countdown the operator can
 * cancel by carrying on.
 */
const SETTLE_SECONDS = 8;

export function TeachPanel({
  recordingId,
  run,
  onSealed,
  onDiscarded,
}: {
  recordingId: string;
  run: number;
  onSealed: (frames: number) => void;
  onDiscarded: () => void;
}) {
  const queryClient = useQueryClient();
  const [countdown, setCountdown] = useState<number | null>(null);
  const [autoSealOff, setAutoSealOff] = useState(false);
  const settled = useRef(false);

  const recording = useQuery({
    queryKey: recordingKeys.detail(recordingId),
    queryFn: () => getRecording(recordingId),
    refetchInterval: (query) => (query.state.data?.status === "capturing" ? 2500 : false),
    // The operator is looking at the browser, not at this tab. Without this the
    // poll pauses the moment the window loses focus, the step count freezes and
    // the completion countdown never starts — while capture carries on happily
    // server-side, which is the worst kind of wrong: silently stale.
    refetchIntervalInBackground: true,
  });

  const liveView = useQuery({
    queryKey: [...recordingKeys.detail(recordingId), "live-view"],
    queryFn: () => getLiveView(recordingId),
    refetchInterval: 20_000,
    refetchIntervalInBackground: true,
  });

  const finish = useMutation({
    mutationFn: (reason?: string) => finishRecording(recordingId, reason),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: recordingKeys.all });
      if (result.status === "sealed") onSealed(result.frame_count);
      else onDiscarded();
    },
    onError: (error) =>
      toast.error("Could not finish the run", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const frames: FrameSummary[] = recording.data?.frames ?? [];
  const appliedFrame = [...frames].reverse().find((frame) => frame.applied);
  const capturing = recording.data?.status === "capturing";

  // The countdown starts once, on the first accepted mutation. Cancelling it
  // means this operator is doing a multi-step task; do not ask again.
  useEffect(() => {
    if (!capturing || settled.current || autoSealOff || !appliedFrame) return;
    settled.current = true;
    setCountdown(SETTLE_SECONDS);
  }, [appliedFrame, capturing, autoSealOff]);

  // One timer that both counts down and fires, so the effect never sets state
  // during its own render pass.
  useEffect(() => {
    if (countdown === null) return;
    const timer = setTimeout(() => {
      if (countdown <= 1) {
        setCountdown(null);
        finish.mutate(undefined);
      } else {
        setCountdown(countdown - 1);
      }
    }, 1000);
    return () => clearTimeout(timer);
    // Re-running on the mutation object would restart the clock every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countdown]);

  const keepRecording = () => {
    setCountdown(null);
    setAutoSealOff(true);
  };

  const url = liveView.data?.live_view_url;

  return (
    <div
      style={{ display: "flex", flexDirection: "column", height: "100%", background: "#E9E9E6" }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "11px 20px",
          background: ink.panel,
          borderBottom: `1px solid ${ink.line}`,
          flex: "0 0 auto",
        }}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <span
            style={{
              width: 9,
              height: 9,
              borderRadius: "50%",
              background: capturing ? ink.danger : ink.textMuted,
              animation: capturing ? "recpulse 1.4s infinite" : undefined,
            }}
          />
          <span style={{ fontSize: 13, fontWeight: 700 }}>
            {capturing ? `Recording · run ${run} of 2` : `Run ${run} finished`}
          </span>
        </span>
        <span style={{ fontSize: 12, color: ink.textSoft }}>
          {frames.length} step{frames.length === 1 ? "" : "s"} captured — gestures, network,
          accessibility tree and screencast
        </span>
        <span style={{ flex: 1 }} />
        {capturing && (
          <>
            <button
              onClick={() => finish.mutate(undefined)}
              disabled={finish.isPending || frames.length === 0}
              style={{
                padding: "8px 15px",
                borderRadius: 8,
                border: `1px solid ${ink.line}`,
                background: ink.panel,
                color: frames.length === 0 ? ink.textMuted : ink.text,
                fontSize: 12.5,
                fontWeight: 600,
                cursor: frames.length === 0 ? "not-allowed" : "pointer",
              }}
              title={frames.length === 0 ? "Do the task in the browser first" : undefined}
            >
              {finish.isPending ? "Finishing…" : "Finish now"}
            </button>
            <button
              onClick={() => finish.mutate("discarded by the operator")}
              style={{
                border: "none",
                background: "transparent",
                fontSize: 12.5,
                fontWeight: 600,
                color: ink.textSoft,
                cursor: "pointer",
                padding: "8px 6px",
              }}
            >
              Discard
            </button>
          </>
        )}
      </header>

      {appliedFrame && capturing && (
        <div
          style={{
            flex: "0 0 auto",
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "10px 20px",
            background: ink.goodWash,
            borderBottom: `1px solid #CBDFCE`,
            color: ink.good,
            fontSize: 13,
          }}
        >
          <span style={{ fontWeight: 700 }}>The system accepted the change.</span>
          <span style={{ fontFamily: mono, fontSize: 11.5 }}>
            {appliedFrame.primary_request} → {appliedFrame.primary_status}
          </span>
          <span style={{ flex: 1 }} />
          {countdown !== null ? (
            <>
              <span>Sealing this run in {countdown}s</span>
              <button
                onClick={keepRecording}
                style={{
                  padding: "6px 12px",
                  borderRadius: 7,
                  border: `1px solid ${ink.good}`,
                  background: "transparent",
                  color: ink.good,
                  fontSize: 12,
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Not done — keep recording
              </button>
            </>
          ) : (
            <span style={{ color: ink.textSoft }}>
              Still recording. Finish when the whole task is done.
            </span>
          )}
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, padding: "18px 20px", display: "flex" }}>
        <div
          style={{
            flex: 1,
            minWidth: 0,
            background: ink.panel,
            border: "1px solid #D5D5D1",
            borderRadius: 10,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            boxShadow: "0 6px 22px rgba(20,20,20,.07)",
          }}
        >
          <div
            style={{
              flex: "0 0 auto",
              display: "flex",
              alignItems: "center",
              gap: 12,
              padding: "9px 12px",
              background: "#F1F1EE",
              borderBottom: "1px solid #DEDEDA",
            }}
          >
            <span style={{ display: "flex", gap: 6 }}>
              {[0, 1, 2].map((dot) => (
                <span
                  key={dot}
                  style={{ width: 10, height: 10, borderRadius: "50%", background: "#D9DAD6" }}
                />
              ))}
            </span>
            <span
              style={{
                flex: 1,
                background: ink.panel,
                border: "1px solid #DEDEDA",
                borderRadius: 6,
                padding: "5px 10px",
                fontFamily: mono,
                fontSize: 11,
                color: ink.textSoft,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {frames.at(-1)?.primary_request?.split(" ")[1] ?? "session"}
            </span>
            <span
              style={{
                fontSize: 10.5,
                fontWeight: 700,
                letterSpacing: ".06em",
                color: ink.textSoft,
              }}
            >
              STEEL SESSION
            </span>
          </div>

          {url ? (
            <iframe
              src={url}
              title="Browser session"
              style={{ flex: 1, width: "100%", border: "none", background: ink.panel }}
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
            />
          ) : (
            <div
              style={{
                flex: 1,
                display: "grid",
                placeItems: "center",
                color: ink.textMuted,
                fontSize: 13,
              }}
            >
              {liveView.isLoading
                ? "Connecting to the browser session…"
                : "The browser session has ended."}
            </div>
          )}
        </div>

        <aside
          style={{
            width: 268,
            flex: "0 0 268px",
            marginLeft: 18,
            display: "flex",
            flexDirection: "column",
            gap: 10,
            overflow: "auto",
          }}
        >
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              letterSpacing: ".08em",
              color: ink.textMuted,
            }}
          >
            CAPTURED SO FAR
          </div>
          {frames.length === 0 && (
            <div style={{ fontSize: 12.5, color: ink.textMuted, lineHeight: 1.6 }}>
              Nothing yet. Do the task in the browser exactly as you normally would.
            </div>
          )}
          {frames.map((frame) => (
            <div
              key={frame.index}
              style={{
                background: ink.panel,
                border: `1px solid ${frame.applied ? "#CBDFCE" : ink.line}`,
                borderRadius: 9,
                padding: "9px 11px",
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5 }}>
                <span style={{ color: ink.textMuted, fontFamily: mono, fontSize: 11 }}>
                  #{frame.index}
                </span>
                <span style={{ fontWeight: 600 }}>{frame.action_kind}</span>
                <span
                  style={{
                    color: ink.textSoft,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {frame.target ?? ""}
                </span>
              </div>
              {frame.primary_request && (
                <div
                  style={{
                    fontFamily: mono,
                    fontSize: 10.5,
                    color: frame.applied ? ink.good : ink.textSoft,
                    wordBreak: "break-all",
                  }}
                >
                  {frame.primary_request}
                  {frame.primary_status ? ` → ${frame.primary_status}` : ""}
                </div>
              )}
              {frame.error_count > 0 && (
                <div style={{ fontSize: 11, color: ink.danger }}>
                  {frame.error_count} error{frame.error_count === 1 ? "" : "s"} on this step
                </div>
              )}
            </div>
          ))}
        </aside>
      </div>

      <div
        style={{ flex: "0 0 auto", padding: "0 20px 16px", fontSize: 11.5, color: ink.barMuted }}
      >
        Everything the page does is captured continuously. Secrets are stored as vault references.
      </div>
    </div>
  );
}
