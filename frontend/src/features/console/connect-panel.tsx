"use client";

import { useCallback, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, ApiError, type Schemas } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * Connecting a system: paste the address, sign in, done.
 *
 * One field, because everything else is already in the URL. A name and a
 * system key made this a form to fill in rather than a link to paste, and got
 * two people naming one system two ways — which silently stops their skills
 * pairing.
 *
 * The sign-in happens in a real window, full size, on the system's own login
 * page. Nothing here sees the password. And nobody has to come back and tell us
 * it worked: the browser is watched until it holds a session for the system's
 * own host, and then everything it holds — cookies for the application and for
 * every identity provider in the chain — is encrypted into the vault.
 *
 * That session is then kept alive by every capture, so this screen is meant to
 * be seen once per system, ever.
 */
export type Connection = Schemas["ConnectionModel"];
type Opened = Schemas["OpenedConnectionResponse"];

export type SessionCheck = Schemas["SessionCheckModel"];

export const connectionKeys = {
  all: ["connections"] as const,
  health: ["connections", "health"] as const,
};

export const listConnections = () => api.get<Connection[]>("/v1/connections");

/**
 * Whether each stored session still works — asked of the systems, not read off
 * a database row. A session that expired an hour ago still says "connected"
 * there, and the operator finds out three clicks into a demonstration.
 */
export const checkSessions = () => api.get<SessionCheck[]>("/v1/connections/health");

/**
 * Sign a connection back in with what it already holds.
 *
 * No credential crosses this call — they were entered once and live in the
 * vault. This only says "now".
 */
export const signInAgain = (connectionId: string, targetSystem: string) =>
  api.post(
    `/v1/connections/${connectionId}/sign-in?target_system=${encodeURIComponent(targetSystem)}`,
  );

export function ConnectPanel({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const [opened, setOpened] = useState<Opened | null>(null);

  const connect = useMutation({
    mutationFn: () => api.post<Opened>("/v1/connections", { base_url: url.trim() }),
    onSuccess: (connection) => {
      setOpened(connection);
      // Full size, in its own window. An identity provider inside a 600px
      // iframe is a login nobody can complete, and some refuse to frame at all.
      window.open(connection.live_view_url, "_blank", "noopener,width=1280,height=900");
    },
    onError: (error) =>
      toast.error("Could not open that address", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  // Stable, or the poll below restarts its timer on every re-render and the
  // two-second tick never actually arrives.
  const finished = useCallback(
    (connection: Connection) => {
      toast.success(`${connection.name} connected`, {
        description: "The session is kept, and kept alive. You will not be asked again.",
      });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.all });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
      onDone();
    },
    [queryClient, onDone],
  );

  return (
    <div style={{ display: "flex", gap: 12 }}>
      <span
        style={{
          width: 26,
          height: 26,
          flex: "0 0 26px",
          borderRadius: "50%",
          background: ink.accent,
          color: "#fff",
          fontSize: 13,
          fontWeight: 800,
          display: "grid",
          placeItems: "center",
        }}
      >
        g
      </span>
      <div
        style={{
          flex: 1,
          border: `1px solid ${ink.line}`,
          borderRadius: 12,
          background: ink.panel,
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {opened ? (
          <Waiting opened={opened} onConnected={finished} onCancel={onDone} />
        ) : (
          <>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Connect a system</div>
            <div style={{ fontSize: 12.5, color: ink.textSoft, lineHeight: 1.6 }}>
              Paste the address once. I will open it, you sign in, and I keep the session — every
              cookie, for the application and for whatever signs you into it.
            </div>
            <input
              value={url}
              autoFocus
              placeholder="https://your-wms.example.com/portal"
              onChange={(event) => setUrl(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && url.trim()) connect.mutate();
              }}
              style={{
                border: `1px solid ${ink.line}`,
                borderRadius: 8,
                padding: "10px 12px",
                fontSize: 13.5,
                fontFamily: mono,
                outline: "none",
              }}
            />
            <button
              onClick={() => connect.mutate()}
              disabled={!url.trim() || connect.isPending}
              style={{
                alignSelf: "flex-start",
                padding: "10px 16px",
                borderRadius: 8,
                border: "none",
                background: url.trim() ? ink.accent : "#E7E7E4",
                color: url.trim() ? "#fff" : ink.textMuted,
                fontSize: 13,
                fontWeight: 700,
                cursor: url.trim() ? "pointer" : "not-allowed",
              }}
            >
              {connect.isPending ? "Opening…" : "Connect"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * The window is open and the operator is signing in. Nothing to press.
 *
 * Asking them to come back and click "I have signed in" was a step that existed
 * only because nobody was watching. The browser is polled instead, and the
 * moment it holds a session for the system's own host — which is what signing
 * in produces, and what an identity provider's own cookies are not — everything
 * is kept.
 */
function Waiting({
  opened,
  onConnected,
  onCancel,
}: {
  opened: Opened;
  onConnected: (connection: Connection) => void;
  onCancel: () => void;
}) {
  const [waited, setWaited] = useState(0);

  useEffect(() => {
    let live = true;
    const keep = () =>
      api.post<Connection>(
        `/v1/connections/${opened.connection_id}/session` +
          `?browser_session_id=${encodeURIComponent(opened.browser_session_id)}`,
      );

    const timer = setInterval(async () => {
      if (!live) return;
      setWaited((seconds) => seconds + 2);
      try {
        const connection = await keep();
        live = false;
        clearInterval(timer);
        onConnected(connection);
      } catch {
        // Still on the login page. The endpoint refuses until a session for
        // this system exists, which is exactly the signal being waited for.
      }
    }, 2000);

    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [opened, onConnected]);

  return (
    <>
      <div style={{ fontSize: 14, fontWeight: 700 }}>Sign in to {opened.name}</div>
      <div style={{ fontSize: 12.5, color: ink.textSoft, lineHeight: 1.6 }}>
        A window is open on the system&rsquo;s own login page. Sign in there — your password is
        typed into that page and reaches nothing of ours. I am watching for the session and will
        take it from there; there is nothing to press when you are done.
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span style={{ fontSize: 12, color: ink.textMuted }}>
          Waiting for the sign-in{waited > 0 ? ` · ${waited}s` : ""}
        </span>
        <a
          href={opened.live_view_url}
          target="_blank"
          rel="noreferrer"
          style={{ fontSize: 12, fontWeight: 700, color: ink.accent }}
        >
          Reopen the window
        </a>
        <span style={{ flex: 1 }} />
        <button
          onClick={onCancel}
          style={{
            border: "none",
            background: "transparent",
            fontSize: 12.5,
            fontWeight: 600,
            color: ink.textSoft,
            cursor: "pointer",
            padding: "6px 4px",
          }}
        >
          Cancel
        </button>
      </div>
      {waited >= 90 && (
        <div style={{ fontSize: 12, color: ink.textSoft, lineHeight: 1.6 }}>
          Still waiting. If the window closed or never opened, reopen it above. If the system signed
          you in but this has not noticed, the session may belong to a different host than the
          address you gave — connect using the address the application itself lands on.
        </div>
      )}
    </>
  );
}
