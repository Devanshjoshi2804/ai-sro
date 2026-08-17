"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, ApiError, type Schemas } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * Connecting a system.
 *
 * Two ways in, and the difference matters.
 *
 * Leave the credential fields empty and the operator signs in on the system's
 * own login page, inside a browser we opened for them. Nothing here sees the
 * password; what is kept is the session it produced.
 *
 * Fill them in and the connection becomes a connector: the credentials are
 * encrypted into the vault, and the system signs itself back in whenever its
 * session expires — at 3am, mid-batch, or before a demonstration that would
 * otherwise have opened on a login page. Nobody is asked a second time.
 *
 * Either way the capture recorder drops credential values where they are typed,
 * so no recording contains one, and no endpoint reads one back out.
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
  const [form, setForm] = useState({
    name: "",
    target_system: "",
    base_url: "",
    username: "",
    password: "",
  });
  const [opened, setOpened] = useState<Opened | null>(null);

  const connect = useMutation({
    mutationFn: async () => {
      const connection = await api.post<Opened>("/v1/connections", {
        name: form.name.trim(),
        target_system: form.target_system.trim(),
        base_url: form.base_url.trim(),
      });
      // Given credentials, the connection signs itself in — now and every time
      // the system expires it afterwards. That is the whole difference between
      // a saved session and a connector: nobody is asked a second time.
      if (form.password) {
        await api.put(`/v1/connections/${connection.connection_id}/credentials`, {
          username: form.username.trim(),
          password: form.password,
        });
        await signInAgain(connection.connection_id, form.target_system.trim());
        return null;
      }
      return connection;
    },
    onSuccess: (connection) => {
      if (connection) {
        setOpened(connection);
        return;
      }
      toast.success(`${form.name} connected`, {
        description: "It will sign itself back in whenever the system expires the session.",
      });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.all });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
      onDone();
    },
    onError: (error) =>
      toast.error("Could not open the system", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const keep = useMutation({
    mutationFn: () =>
      api.post<Connection>(
        `/v1/connections/${opened?.connection_id}/session` +
          `?browser_session_id=${encodeURIComponent(opened?.browser_session_id ?? "")}`,
      ),
    onSuccess: (connection) => {
      toast.success(`${connection.name} connected`, {
        description: "The session is encrypted in the vault. Demonstrations start signed in.",
      });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.all });
      onDone();
    },
    onError: (error) =>
      toast.error("Not signed in yet", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  // Credentials are optional, so they are not part of "complete" -- but half a
  // credential is worse than none, since it would be stored and then fail every
  // unattended sign-in from here on.
  const complete =
    [form.name, form.target_system, form.base_url].every((value) => value.trim().length > 0) &&
    Boolean(form.username.trim()) === Boolean(form.password);

  if (opened) {
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
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 700 }}>Sign in to {form.name}</span>
          <span style={{ fontSize: 12, color: ink.textSoft }}>
            Use the system&rsquo;s own login. Your password is typed into that page and is never
            sent to us, stored, or written into a recording.
          </span>
          <span style={{ flex: 1 }} />
          <button
            onClick={() => keep.mutate()}
            disabled={keep.isPending}
            style={{
              padding: "8px 15px",
              borderRadius: 8,
              border: "none",
              background: ink.accent,
              color: "#fff",
              fontSize: 12.5,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {keep.isPending ? "Keeping the session…" : "I have signed in"}
          </button>
          <button
            onClick={onDone}
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
            Cancel
          </button>
        </header>

        <div style={{ flex: 1, minHeight: 0, padding: "18px 20px" }}>
          <iframe
            src={opened.live_view_url}
            title="Sign in"
            style={{
              width: "100%",
              height: "100%",
              border: "1px solid #D5D5D1",
              borderRadius: 10,
              background: ink.panel,
            }}
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups"
          />
        </div>
      </div>
    );
  }

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
        <div style={{ fontSize: 14, fontWeight: 700 }}>Connect a system</div>
        <div style={{ fontSize: 12.5, color: ink.textSoft, lineHeight: 1.6 }}>
          Give me the address and I will open it. You sign in there; I keep the session, encrypted,
          so demonstrations and replays do not ask you again.
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {(
            [
              ["name", "Name", "Blue Yonder SCE"],
              ["target_system", "System key", "blue_yonder"],
            ] as const
          ).map(([key, label, placeholder]) => (
            <label key={key} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: ink.textMuted }}>{label}</span>
              <input
                value={form[key]}
                placeholder={placeholder}
                onChange={(event) => setForm({ ...form, [key]: event.target.value })}
                style={{
                  border: `1px solid ${ink.line}`,
                  borderRadius: 8,
                  padding: "8px 10px",
                  fontSize: 13,
                  fontFamily: mono,
                  outline: "none",
                }}
              />
            </label>
          ))}
          <label style={{ gridColumn: "1 / -1", display: "flex", flexDirection: "column", gap: 5 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: ink.textMuted }}>Address</span>
            <input
              value={form.base_url}
              placeholder="https://wms.example.com/portal"
              onChange={(event) => setForm({ ...form, base_url: event.target.value })}
              style={{
                border: `1px solid ${ink.line}`,
                borderRadius: 8,
                padding: "8px 10px",
                fontSize: 13,
                fontFamily: mono,
                outline: "none",
              }}
            />
          </label>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {(
            [
              ["username", "Username", "text", "operator@company.com"],
              ["password", "Password", "password", "kept encrypted, never shown again"],
            ] as const
          ).map(([key, label, type, placeholder]) => (
            <label key={key} style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: ink.textMuted }}>{label}</span>
              <input
                type={type}
                value={form[key]}
                placeholder={placeholder}
                autoComplete={key === "password" ? "new-password" : "username"}
                onChange={(event) => setForm({ ...form, [key]: event.target.value })}
                style={{
                  border: `1px solid ${ink.line}`,
                  borderRadius: 8,
                  padding: "8px 10px",
                  fontSize: 13,
                  fontFamily: mono,
                  outline: "none",
                }}
              />
            </label>
          ))}
        </div>
        <div style={{ fontSize: 11.5, color: ink.textSoft, lineHeight: 1.6 }}>
          Optional. With them, this system signs itself back in whenever its session expires — you
          are never asked again. They are encrypted in the vault, never shown, never returned by any
          request, never written into a recording, and typed into no page but this system&rsquo;s
          own login. Leave them empty to sign in by hand instead.
        </div>
        <button
          onClick={() => connect.mutate()}
          disabled={!complete || connect.isPending}
          style={{
            alignSelf: "flex-start",
            padding: "10px 16px",
            borderRadius: 8,
            border: "none",
            background: complete ? ink.accent : "#E7E7E4",
            color: complete ? "#fff" : ink.textMuted,
            fontSize: 13,
            fontWeight: 700,
            cursor: complete ? "pointer" : "not-allowed",
          }}
        >
          {connect.isPending ? "Opening…" : "Open the login page"}
        </button>
      </div>
    </div>
  );
}
