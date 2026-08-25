"use client";

import { useState, useSyncExternalStore } from "react";
import {
  forget,
  looksLikeAToken,
  onCredentialChange,
  remember,
  usableCredential,
  whoAmI,
} from "@/lib/api/credential";
import { ink, mono } from "@/features/console/theme";

/**
 * Nothing loads until this browser has a credential.
 *
 * Not a login form — there is no user store, and inventing one would be a
 * password database nobody asked for. Somebody with shell access mints a token
 * and the operator pastes it once; it is signed, it expires, and everything
 * the tenant sees is decided by it rather than by a header.
 */
export function SignInGate({ children }: { children: React.ReactNode }) {
  // localStorage does not exist while this renders on the server, so the held
  // credential is read once the component is mounted in a browser. `useSyncExternalStore`
  // rather than an effect: it gives the server pass and the first client pass
  // the same answer without a setState that re-renders everything under it.
  const held = useSyncExternalStore(onCredentialChange, usableCredential, () => null);
  const [typed, setTyped] = useState("");
  const [refused, setRefused] = useState<string | null>(null);

  if (!held) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: ink.page,
          padding: 24,
        }}
      >
        <div
          style={{
            width: 460,
            maxWidth: "100%",
            background: ink.panel,
            border: `1px solid ${ink.line}`,
            borderRadius: 14,
            padding: 28,
            display: "flex",
            flexDirection: "column",
            gap: 16,
            boxShadow: "0 12px 40px rgba(0,0,0,0.06)",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span
              style={{
                fontFamily: mono,
                fontSize: 10.5,
                letterSpacing: 1.4,
                color: ink.accent,
                fontWeight: 700,
              }}
            >
              AI-SRO
            </span>
            <h1 style={{ fontSize: 21, fontWeight: 700, margin: 0, letterSpacing: -0.3 }}>
              Sign in
            </h1>
            <p style={{ fontSize: 13, color: ink.textSoft, margin: 0, lineHeight: 1.55 }}>
              Your credential decides which warehouse you can see and puts your name
              on every write you authorise.
            </p>
          </div>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 10.5, fontWeight: 700, color: ink.textMuted, letterSpacing: 0.5 }}>
              CREDENTIAL
            </span>
            <textarea
              value={typed}
              autoFocus
              spellCheck={false}
              onChange={(event) => {
                setTyped(event.target.value);
                setRefused(null);
              }}
              onKeyDown={(event) => {
                // Enter submits; a credential is one line, however it wraps.
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  accept(typed, setRefused);
                }
              }}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…"
              rows={3}
              style={{
                fontFamily: mono,
                fontSize: 11.5,
                lineHeight: 1.5,
                padding: 10,
                borderRadius: 8,
                border: `1px solid ${refused ? ink.danger : ink.line}`,
                resize: "vertical",
                outline: "none",
                wordBreak: "break-all",
              }}
            />
          </label>

          {refused && <span style={{ fontSize: 12, color: ink.danger }}>{refused}</span>}

          <button
            onClick={() => accept(typed, setRefused)}
            style={{
              padding: "10px 14px",
              borderRadius: 8,
              border: "none",
              background: ink.accent,
              color: "#fff",
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Continue
          </button>

          {/* Where one comes from. A sign-in screen that assumes you already
              have the thing it is asking for is a dead end. */}
          <div
            style={{
              borderTop: `1px solid ${ink.lineSoft}`,
              paddingTop: 12,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <span style={{ fontSize: 11.5, color: ink.textMuted }}>
              Don&rsquo;t have one? Whoever runs this deployment issues it:
            </span>
            <code
              style={{
                fontFamily: mono,
                fontSize: 11,
                background: ink.page,
                border: `1px solid ${ink.line}`,
                borderRadius: 6,
                padding: "7px 9px",
                color: ink.textSoft,
              }}
            >
              make token tenant=acme principal=you
            </code>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {children}
      <SignedInAs
        onForget={() => {
          forget();
          setTyped("");
        }}
      />
    </>
  );
}

function accept(typed: string, refuse: (why: string | null) => void): void {
  const token = typed.trim();
  // Checked here only so a typo says so immediately; the signature itself is
  // checked by the backend on every single request.
  if (!looksLikeAToken(token)) {
    refuse("That does not look like a credential this system issued.");
    return;
  }
  // `remember` tells the gate itself; nothing else has to.
  remember(token);
}


function SignedInAs({ onForget }: { onForget: () => void }) {
  const me = whoAmI();
  if (!me) return null;
  return (
    <button
      onClick={onForget}
      title="Forget this credential on this browser"
      style={{
        position: "fixed",
        right: 12,
        bottom: 12,
        zIndex: 60,
        padding: "5px 9px",
        borderRadius: 999,
        border: `1px solid ${ink.line}`,
        background: ink.panel,
        color: ink.textMuted,
        fontFamily: mono,
        fontSize: 10.5,
        cursor: "pointer",
      }}
    >
      {me.principal} · {me.tenant} · sign out
    </button>
  );
}
