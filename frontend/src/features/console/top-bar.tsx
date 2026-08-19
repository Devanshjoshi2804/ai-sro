"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ink } from "@/features/console/theme";
import { whoAmI } from "@/lib/api/credential";

/**
 * One bar across every surface.
 *
 * The console and the review pages are the same product seen by two people: an
 * operator teaching, and a supervisor deciding whether the result may be
 * promoted. Two visual languages would make the review page look like a
 * different, older tool — which is exactly how a reviewer stops trusting it.
 */
export function TopBar({ children, tenant }: { children?: ReactNode; tenant?: string }) {
  // Read from the credential, never defaulted. A hardcoded "acme" said acme
  // over a console signed in as another tenant, which is the one label in the
  // whole application that has to be right: it is what tells somebody which
  // warehouse they are about to write to.
  const signedInAs = tenant ?? whoAmI()?.tenant ?? "—";
  return (
    <nav
      style={{
        display: "flex",
        alignItems: "stretch",
        background: ink.bar,
        padding: "0 14px",
        height: 46,
        flex: "0 0 auto",
        fontFamily: "Manrope, var(--font-geist-sans), sans-serif",
      }}
    >
      <Link
        href="/console"
        style={{ display: "flex", alignItems: "center", gap: 9, paddingRight: 18 }}
      >
        <span
          style={{
            width: 20,
            height: 20,
            borderRadius: "50%",
            background: ink.accent,
            color: "#fff",
            fontWeight: 800,
            fontSize: 13,
            display: "grid",
            placeItems: "center",
          }}
        >
          g
        </span>
        <span style={{ fontSize: 13.5, fontWeight: 700, color: ink.barText }}>
          Grey<span style={{ color: ink.accent }}>Orange</span>{" "}
          <span style={{ color: ink.barMuted, fontWeight: 600 }}>AI-SRO</span>
        </span>
      </Link>

      {children}

      <span style={{ flex: 1 }} />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          fontSize: 11.5,
          color: "#7A7C7F",
          fontWeight: 600,
        }}
      >
        <span>
          tenant <span style={{ color: ink.barText }}>{signedInAs}</span>
        </span>
        <span
          style={{
            padding: "3px 8px",
            border: "1px solid #3A3C3F",
            borderRadius: 5,
            color: ink.barText,
          }}
        >
          LADDER · EARNED, NOT SET
        </span>
      </div>
    </nav>
  );
}

export function BarLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      style={{
        display: "flex",
        alignItems: "center",
        padding: "0 14px",
        fontSize: 12.5,
        fontWeight: 600,
        color: "#8A8C8F",
      }}
    >
      {children}
    </Link>
  );
}
