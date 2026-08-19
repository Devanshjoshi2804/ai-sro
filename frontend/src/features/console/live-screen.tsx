"use client";

import { useEffect, useRef, useState } from "react";
import { credential } from "@/lib/api/credential";
import { env } from "@/lib/env";
import { ink, mono } from "@/features/console/theme";

/**
 * The screen of one browser session, live.
 *
 * Not the provider's viewer. Self-hosted Steel hands out a single `debugUrl`
 * for the whole deployment with no session in it, so "Watch it" opened either
 * somebody else's browser or a page that said "Session connecting…" forever
 * about a session released an hour before. This is addressed by session id and
 * shows what that session's Chrome is painting, over `/v1/browser/{id}/live`.
 *
 * View-only. Teaching happens in a browser the operator drives themselves; what
 * this is for is watching work being done on their behalf.
 */
export function LiveScreen({ sessionId, height = 420 }: { sessionId: string; height?: number }) {
  const image = useRef<HTMLImageElement>(null);
  const [state, setState] = useState<"connecting" | "live" | "ended">("connecting");

  useEffect(() => {
    const token = credential();
    if (!token) return;

    // A websocket cannot carry an Authorization header and a token in the query
    // string is a token in every access log; the subprotocol list can hold it.
    const socket = new WebSocket(
      `${env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws")}/v1/browser/${sessionId}/live`,
      ["bearer", token],
    );
    socket.binaryType = "blob";

    let showing: string | null = null;
    socket.onmessage = (event) => {
      const next = URL.createObjectURL(event.data as Blob);
      if (image.current) image.current.src = next;
      // Revoked one frame late, not immediately: the <img> has not decoded the
      // new blob yet, and dropping it here leaves a broken frame on screen.
      if (showing) URL.revokeObjectURL(showing);
      showing = next;
      setState("live");
    };
    socket.onclose = () => setState("ended");
    socket.onerror = () => setState("ended");

    return () => {
      socket.close();
      if (showing) URL.revokeObjectURL(showing);
    };
  }, [sessionId]);

  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 8,
        overflow: "hidden",
        background: "#0b0b0d",
        height,
        display: "grid",
        placeItems: "center",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={image}
        alt={`Browser session ${sessionId}`}
        style={{
          maxWidth: "100%",
          maxHeight: "100%",
          display: state === "live" ? "block" : "none",
        }}
      />
      {state !== "live" && (
        <span style={{ fontSize: 11.5, color: ink.textMuted, fontFamily: mono }}>
          {state === "connecting"
            ? "attaching to the session…"
            : "the browser session has ended — nothing left to watch"}
        </span>
      )}
    </div>
  );
}
