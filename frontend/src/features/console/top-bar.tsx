"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ink } from "@/features/console/theme";
import { forget, whoAmI } from "@/lib/api/credential";

/**
 * One bar across every surface.
 *
 * The console and the review pages are the same product seen by two people: an
 * operator teaching, and a supervisor deciding whether the result may be
 * promoted. Two visual languages would make the review page look like a
 * different, older tool — which is exactly how a reviewer stops trusting it.
 */
export function TopBar({
  children,
  tenant,
  right,
}: {
  children?: ReactNode;
  tenant?: string;
  right?: ReactNode;
}) {
  // Read from the credential, never defaulted. A hardcoded "acme" said acme
  // over a console signed in as another tenant, which is the one label in the
  // whole application that has to be right: it is what tells somebody which
  // warehouse they are about to write to.
  const signedInAs = tenant ?? whoAmI()?.tenant ?? "—";
  return (
    <nav
      data-chrome="bar"
      style={{
        display: "flex",
        alignItems: "stretch",
        background: ink.bar,
        borderBottom: `1px solid ${ink.line}`,
        padding: "0 14px",
        height: 46,
        // The BAR does not scroll; the links inside it do. When the bar
        // scrolled as a whole, adding the five workflow pages pushed the
        // tenant name and the sign-out button off the right-hand edge at
        // 1512px -- and that label is, by this file's own rule, the one that
        // has to be right, because it says which warehouse you are about to
        // write to. A control you have to go looking for is not on the bar.
        overflow: "hidden",
        flex: "0 0 auto",
        fontFamily: "var(--font-display), system-ui, sans-serif",
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

      {/* Below about 700px the last group used to fall off the end with
          nothing to say it was there. Scrolling is still the smallest honest
          answer; a menu is a second navigation to keep in step. `minWidth: 0`
          is what lets a flex child actually shrink and scroll rather than
          forcing its parent wider. */}
      <div
        style={{
          display: "flex",
          alignItems: "stretch",
          flex: "1 1 auto",
          minWidth: 0,
          overflowX: "auto",
          scrollbarWidth: "none",
        }}
      >
        {children}
      </div>

      {right}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          fontSize: 11.5,
          color: ink.textMuted,
          fontWeight: 600,
          flex: "0 0 auto",
          paddingLeft: 14,
        }}
      >
        {/* Signing out lives here rather than in a pill fixed to the corner of
            the viewport, which covered a table row on Runs and the sentence
            about where capture is stored on the console. This bar already had
            to name the tenant correctly; now it is also the way out. */}
        <button
          type="button"
          onClick={() => forget()}
          title="Forget this credential on this browser"
          style={{
            padding: "3px 8px",
            border: `1px solid ${ink.line}`,
            borderRadius: 5,
            background: "transparent",
            color: ink.textMuted,
            font: "inherit",
            fontSize: 11.5,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          tenant <span style={{ color: ink.barText }}>{signedInAs}</span> · sign out
        </button>
      </div>
    </nav>
  );
}

/**
 * A link that knows whether you are standing on it.
 *
 * Every link in this bar rendered the same grey, including the one for the page
 * you were already looking at, so the only thing telling a supervisor where
 * they were was the `<h1>`. `aria-current` as well as the underline: the colour
 * is not the answer for somebody who cannot see it.
 */
export function BarLink({ href, children }: { href: string; children: ReactNode }) {
  const pathname = usePathname();
  // Prefix rather than equality, or `/skills/skl_…` would light nothing.
  const here = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      aria-current={here ? "page" : undefined}
      style={{
        display: "flex",
        alignItems: "center",
        flex: "0 0 auto",
        whiteSpace: "nowrap",
        padding: "0 14px",
        fontSize: 12.5,
        fontWeight: 600,
        color: here ? ink.text : ink.textMuted,
        boxShadow: here ? `inset 0 -2px 0 ${ink.accent}` : undefined,
      }}
    >
      {children}
    </Link>
  );
}

/** The name of a group of links, so eight siblings read as four jobs. */
export function BarGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", flex: "0 0 auto" }}>
      <span
        style={{
          alignSelf: "center",
          paddingLeft: 14,
          whiteSpace: "nowrap",
          fontFamily: "var(--font-mono-face), monospace",
          fontSize: 9.5,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: ink.textMuted,
        }}
      >
        {label}
      </span>
      {children}
    </div>
  );
}
