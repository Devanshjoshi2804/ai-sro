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
  const [state, setState] = useState<"connecting" | "live" | "ended" | "unreachable">(
    "connecting",
  );

  // Back to "connecting" the moment the session changes, and the last frame
  // cleared with it. Neither happened before, so browser B opened showing the
  // last thing browser A painted -- presented as live, with a caption saying so.
  // Adjusting during render rather than in an effect is React's own answer to
  // this: an effect would paint the stale frame first.
  // The frame itself is hidden whenever this is not "live", so clearing the
  // element is unnecessary -- what mattered was that the caption and the
  // visibility went back to connecting.
  const [watching, setWatching] = useState(sessionId);
  if (watching !== sessionId) {
    setWatching(sessionId);
    setState("connecting");
  }

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
    // Closed by the far end, which is the session really being over.
    socket.onclose = () => setState((was) => (was === "live" ? "ended" : "unreachable"));
    // Not the same thing: a socket that never opened is this deployment being
    // unreachable, and reporting it as "the session has ended" sent operators
    // to reconnect a system that was never disconnected.
    socket.onerror = () => setState((was) => (was === "live" ? "ended" : "unreachable"));

    return () => {
      // Every handler dropped first: a frame arriving during teardown creates
      // one more object URL after the last revoke, and a session watched for an
      // hour leaked one per frame.
      socket.onmessage = null;
      socket.onclose = null;
      socket.onerror = null;
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
            : state === "ended"
              ? "the browser session has ended — nothing left to watch"
              : "cannot reach the live view from here"}
        </span>
      )}
    </div>
  );
}
