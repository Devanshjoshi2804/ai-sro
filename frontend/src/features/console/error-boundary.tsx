"use client";

import { Component, type ReactNode } from "react";
import { ink } from "@/features/console/theme";

/**
 * One thrown render does not take the console with it.
 *
 * React unmounts the whole tree when a render throws, and the console's
 * transcript lives only in this browser — so a single malformed value in one
 * step of one run took the operator to a white screen and lost every question
 * they had asked and every answer they had been given.
 *
 * Deliberately a class: this is the one thing hooks cannot do.
 */
export class ConsoleErrorBoundary extends Component<
  { children: ReactNode },
  { failed: Error | null }
> {
  state: { failed: Error | null } = { failed: null };

  static getDerivedStateFromError(error: Error): { failed: Error } {
    return { failed: error };
  }

  render(): ReactNode {
    const { failed } = this.state;
    if (!failed) return this.props.children;
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
            width: 520,
            maxWidth: "100%",
            background: ink.panel,
            border: `1px solid ${ink.line}`,
            borderRadius: 14,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <h1 style={{ margin: 0, fontSize: 15, color: ink.text }}>The console stopped drawing</h1>
          <p style={{ margin: 0, fontSize: 12.5, color: ink.textSoft, lineHeight: 1.55 }}>
            Nothing was sent to the warehouse by this. Runs that had already started are still
            running, and what they did is on the runs page.
          </p>
          <code
            style={{
              fontSize: 11.5,
              color: ink.textMuted,
              background: ink.page,
              borderRadius: 8,
              padding: "8px 10px",
              overflowX: "auto",
            }}
          >
            {failed.message}
          </code>
          <button
            onClick={() => this.setState({ failed: null })}
            style={{
              alignSelf: "flex-start",
              border: "none",
              borderRadius: 8,
              padding: "7px 12px",
              background: ink.accent,
              color: "#fff",
              fontSize: 12.5,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Try drawing it again
          </button>
        </div>
      </div>
    );
  }
}
