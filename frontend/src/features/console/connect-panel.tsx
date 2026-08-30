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

export type OpenBrowser = Schemas["OpenBrowserModel"];

export const connectionKeys = {
  all: ["connections"] as const,
  health: ["connections", "health"] as const,
  browsers: ["connections", "browsers"] as const,
};

/**
 * Browsers this deployment is driving right now.
 *
 * Signing in, replaying a screen, pursuing a goal — all of it happens in a
 * window nobody can see, and "it did not finish" is not something anybody can
 * act on. A link to watch it is the difference between diagnosing a consent
 * screen and guessing.
 */
export const openBrowsers = () => api.get<OpenBrowser[]>("/v1/connections/browsers");

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

export function ConnectPanel({
  onDone,
  reconnect,
}: {
  onDone: () => void;
  /** An existing connection whose session died. Its address is already known,
   * so there is no form to fill in — the browser opens and the watching starts
   * at once. Without this, "sign in again" opened a window nothing was
   * polling, and an operator signed in successfully while the console went on
   * reporting them signed out. */
  reconnect?: { base_url: string };
}) {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState(reconnect?.base_url ?? "");
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

  // A known address needs no form: open it and start watching.
  const begin = connect.mutate;
  useEffect(() => {
    if (reconnect) begin();
    // Once, for the connection this panel was opened for.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reconnect?.base_url]);

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
                background: url.trim() ? ink.accent : ink.disabled,
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


/**
 * What the stored session is actually worth, right now.
 *
 * The row used to read "session held" whenever the database said connected,
 * which stayed true for weeks after the system had forgotten the session. An
 * operator only found out by being shown a login page inside a demonstration.
 * Now a dead session says so here, with the one action that fixes it.
 */
export function SessionState({
  check,
  status,
  connection,
  onReconnect,
}: {
  check?: SessionCheck;
  status: string;
  connection: { id: string; target_system: string };
  onReconnect: () => void;
}) {
  const queryClient = useQueryClient();
  // Tried first, because a connection that holds credentials should never make
  // anybody type them a second time. Only when there are none does the operator
  // get the login page.
  const retry = useMutation({
    mutationFn: () => signInAgain(connection.id, connection.target_system),
    onSuccess: () => {
      toast.success("Signed back in", { description: "Nobody had to be asked." });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
    },
    // No stored credentials is the common case, not an error worth a toast:
    // it means this system is signed into by hand, so open the window and
    // watch it. What went wrong before was opening one nothing was watching.
    onError: onReconnect,
  });
  const state = check?.health ?? (status === "connected" ? "checking" : "never_connected");
  const { dot, label } = {
    signed_in: { dot: ink.goodDot, label: "signed in" },
    signed_out: { dot: ink.danger, label: "signed out" },
    never_connected: { dot: ink.textMuted, label: "not connected" },
    // An outage is not a bad session, and asking for a password would not fix
    // one. Say what is true: we could not ask.
    unreachable: { dot: ink.warn, label: "system not answering" },
    checking: { dot: ink.textMuted, label: "checking…" },
  }[state] ?? { dot: ink.textMuted, label: state };

  return (
    <span style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: dot }} />
        <span style={{ fontSize: 11, color: ink.textSoft }}>{label}</span>
      </span>
      {(state === "signed_out" || state === "never_connected") && (
        <button
          onClick={() => retry.mutate()}
          disabled={retry.isPending}
          style={{
            alignSelf: "flex-start",
            padding: 0,
            border: "none",
            background: "transparent",
            fontSize: 11,
            fontWeight: 700,
            color: ink.accent,
            cursor: "pointer",
          }}
        >
          {retry.isPending ? "Signing in…" : "Sign in again"}
        </button>
      )}
      {(state === "signed_out" || state === "never_connected") && (
        <KeepSignedIn connectionId={connection.id} system={connection.target_system} />
      )}
    </span>
  );
}

/**
 * Sign this system in by itself, from now on.
 *
 * The identity provider will not issue this deployment a credential of its
 * own: the WMS client is public and permitted one flow, and the realm accepts
 * only the redirect the application itself registered. So the way to stop an
 * expired session interrupting work is the way a person would do it — open the
 * system's own login page and sign in — done by the system, on its own, at the
 * moment it finds itself signed out.
 *
 * The password is typed into that page and nowhere else. It is encrypted in
 * the vault, returned by no request, written into no recording, and used
 * against no host but this connection's own.
 */
function KeepSignedIn({ connectionId, system }: { connectionId: string; system: string }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ username: "", password: "" });

  const keep = useMutation({
    mutationFn: async () => {
      await api.put(`/v1/connections/${connectionId}/credentials`, {
        username: form.username.trim(),
        password: form.password,
      });
      // This connection's own system. It was the literal `blue_yonder`
      // while the sibling call one line up threaded the real one, so on any
      // other connection the operator typed a real password, the credential
      // was stored, the sign-in failed, and nothing rolled back.
      return api.post(
        `/v1/connections/${connectionId}/sign-in?target_system=${encodeURIComponent(system)}`,
      );
    },
    onSuccess: () => {
      toast.success("It will sign itself in from now on");
      setOpen(false);
      setForm({ username: "", password: "" });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
    },
    onError: (error) =>
      toast.error("Could not sign in", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          alignSelf: "flex-start",
          padding: 0,
          border: "none",
          background: "transparent",
          fontSize: 11,
          color: ink.textMuted,
          cursor: "pointer",
          textDecoration: "underline",
        }}
      >
        Stop asking me
      </button>
    );
  }

  const ready = form.username.trim() && form.password;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, paddingTop: 4 }}>
      {(["username", "password"] as const).map((field) => (
        <input
          key={field}
          type={field === "password" ? "password" : "text"}
          value={form[field]}
          placeholder={field}
          autoComplete={field === "password" ? "new-password" : "username"}
          onChange={(event) => setForm({ ...form, [field]: event.target.value })}
          style={{
            border: `1px solid ${ink.line}`,
            borderRadius: 6,
            padding: "5px 7px",
            fontSize: 11.5,
            fontFamily: mono,
            outline: "none",
          }}
        />
      ))}
      <button
        onClick={() => keep.mutate()}
        disabled={!ready || keep.isPending}
        style={{
          border: "none",
          borderRadius: 6,
          padding: "5px 8px",
          background: ready ? ink.accent : ink.disabled,
          color: ready ? "#fff" : ink.textMuted,
          fontSize: 11,
          fontWeight: 700,
          cursor: ready ? "pointer" : "not-allowed",
        }}
      >
        {keep.isPending ? "Signing in…" : "Keep me signed in"}
      </button>
      <span style={{ fontSize: 10, color: ink.textMuted, lineHeight: 1.5 }}>
        Encrypted in the vault, typed into this system&rsquo;s own login page and nowhere else.
      </span>
    </div>
  );
}
