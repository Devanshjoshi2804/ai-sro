"use client";

import { useEffect, useState } from "react";
import { ink, mono } from "@/features/console/theme";
import type { RunModel } from "@/features/run/api";
import type { RunStep, Waiting } from "@/features/run/stream";

/**
 * A run happening in the operator's own Chrome.
 *
 * The console does not contain that browser and must never pretend to: no
 * simulated chrome, no address bar, no cursor. What it can do is make a browser
 * the operator already trusts legible — where it is acting, how it found each
 * control, and when it is deliberately holding back because they are typing.
 *
 * No screen is shown, and the card says so. `RemoteUiDriver.capture` decodes a
 * screenshot into memory for the vision rung and drops it; a run keeps none, by
 * a decision `docs/14-extension-protocol.md` records. A blank panel promising
 * one would be worse than the sentence.
 */
export function InYourBrowser({
  steps,
  waiting,
  of,
  where,
  browser,
  finished,
  onStop,
  stopping,
}: {
  steps: RunStep[];
  waiting: Waiting | null;
  /** How many steps the version has, so "4 of 8" is not "4 so far". */
  of: number | null;
  /** The origin the run is acting on, from the last step that named one. */
  where: string | null;
  /** What the operator calls the machine this is happening on. */
  browser: string | null;
  finished: boolean;
  /** Absent for a run this console cannot stop, so the control is not drawn
   * rather than drawn and refused. */
  onStop?: () => void;
  stopping?: boolean;
}) {
  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 9,
        overflow: "hidden",
        background: ink.panel,
      }}
    >
      <Header steps={steps.length} of={of} where={where} browser={browser} finished={finished} />
      {waiting && <Held key={`${waiting.index}-${waiting.heldMs}`} waiting={waiting} />}
      <ol style={{ margin: 0, padding: "8px 12px", listStyle: "none", display: "grid", gap: 5 }}>
        {steps.map((step) => (
          <Step key={`${step.index}-${step.iteration ?? 0}`} step={step} />
        ))}
        {steps.length === 0 && (
          <li style={{ fontSize: 11.5, color: ink.textMuted }}>Opening the connection…</li>
        )}
      </ol>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 10,
          padding: "8px 12px",
          borderTop: `1px solid ${ink.lineSoft}`,
          fontSize: 11,
          color: ink.textMuted,
        }}
      >
        <span>No screen is kept — this is happening in the tab in front of you.</span>
        {onStop && !finished && (
          <button
            type="button"
            onClick={onStop}
            disabled={stopping}
            style={{
              marginLeft: "auto",
              padding: "4px 10px",
              borderRadius: 6,
              border: `1px solid ${ink.danger}`,
              background: "transparent",
              color: ink.danger,
              font: "inherit",
              fontSize: 11,
              fontWeight: 600,
              cursor: stopping ? "default" : "pointer",
            }}
          >
            {/* Named for when it happens, not for the press. It ends at the
                next step -- a gesture already sent cannot be recalled -- and a
                button that looked instant would be lying about a warehouse. */}
            {stopping ? "Stopping at the next step…" : "Stop this run"}
          </button>
        )}
      </div>
    </div>
  );
}

function Header({
  steps,
  of,
  where,
  browser,
  finished,
}: {
  steps: number;
  of: number | null;
  where: string | null;
  browser: string | null;
  finished: boolean;
  /** Absent for a run this console cannot stop, so the control is not drawn
   * rather than drawn and refused. */
  onStop?: () => void;
  stopping?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 8,
        padding: "8px 12px",
        background: ink.accentWash,
        borderBottom: `1px solid ${ink.lineSoft}`,
      }}
    >
      {!finished && (
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: 999,
            background: ink.accent,
            animation: "sro-beat 1.1s ease-in-out infinite",
          }}
        />
      )}
      <span style={{ fontSize: 12, fontWeight: 700 }}>
        {finished ? "Ran" : "Running"} {of === null ? `${steps} steps` : `step ${steps} of ${of}`}
      </span>
      {/* Named, always. A run may act in a tab the operator is not looking at,
          and a machine doing that without saying where is indistinguishable
          from one that should not be trusted with it. The protocol carries an
          origin and no tab id, so this says a host and never "tab 2". */}
      {where && (
        <span style={{ fontFamily: mono, fontSize: 11, color: ink.textSoft }}>on {where}</span>
      )}
      {browser && (
        <span style={{ fontSize: 11, color: ink.textMuted, marginLeft: "auto" }}>{browser}</span>
      )}
    </div>
  );
}

/**
 * The machine deferring to the person.
 *
 * The extension says it is busy while the operator types, and the backend holds
 * its commands. Rendered as *less* energy, never a new spinner: deference that
 * announces itself louder than the work is not deference. The countdown runs
 * locally because the event is sent only when the state changes.
 */
function Held({ waiting }: { waiting: Waiting }) {
  // The deadline is fixed when this mounts, and the parent remounts it on a new
  // `waiting`. Copying a prop into state inside an effect would be the same
  // countdown with an extra render and a way to disagree with itself.
  const [ends] = useState(() => Date.now() + (waiting.heldMs ?? 0));
  const [now, setNow] = useState(() => Date.now());
  const left = Math.max(0, ends - now);

  useEffect(() => {
    if (!waiting.heldMs) return;
    const tick = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(tick);
  }, [waiting.heldMs]);

  return (
    <p
      style={{
        margin: 0,
        padding: "7px 12px",
        borderBottom: `1px solid ${ink.lineSoft}`,
        background: ink.panel,
        fontSize: 11.5,
        color: ink.textSoft,
      }}
    >
      <span style={{ color: ink.text, fontWeight: 600 }}>Held — you are typing.</span>{" "}
      {left > 0 ? `Resuming in ${(left / 1000).toFixed(1)}s, or the moment you stop.` : "Resuming."}
    </p>
  );
}

function Step({ step }: { step: RunStep }) {
  // `Answer.detail` prefixes the kind the extension named, so a run that chose
  // not to steal the operator's screen can be told apart from one that could
  // not find a control. Behaving well should not read as a fault.
  const declined = step.detail?.startsWith("focus_not_permitted");
  const withheld = step.disposition === "withheld";

  return (
    <li
      style={{
        display: "grid",
        gap: 2,
        fontFamily: mono,
        fontSize: 11,
        color: ink.textSoft,
        animation: "sro-land 220ms ease-out",
      }}
    >
      <span style={{ display: "flex", gap: 8, alignItems: "baseline" }}>
        <Mark disposition={step.disposition} />
        <span style={{ color: ink.text }}>{step.method ?? step.medium}</span>
        <span
          style={{
            flex: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {pathOf(step.url) ?? step.intent}
        </span>
        {/* How it found the control, which is the difference between a replay
            and a guess -- and it was already on the wire. */}
        {step.matched_by && <span style={{ color: ink.textMuted }}>by {step.matched_by}</span>}
        {step.status_code !== null && <span>{step.status_code}</span>}
      </span>
      {declined && (
        <span style={{ color: ink.info }}>
          Did not bring the tab to the front — this run was not allowed to take your screen.
        </span>
      )}
      {/* A shadow run produces the write in full and does not send it. Nothing
          else in this product can show a warehouse write that did not happen,
          and for a UI step the withheld write is a sentence rather than a body. */}
      {withheld && (
        <span style={{ color: ink.warn }}>
          Withheld: {step.request_body ?? step.detail ?? "the write this step would have made"}
        </span>
      )}
    </li>
  );
}

function Mark({ disposition }: { disposition: string }) {
  const tone =
    disposition === "failed"
      ? ink.danger
      : disposition === "withheld"
        ? ink.warn
        : disposition === "skipped"
          ? ink.textMuted
          : ink.good;
  return <span style={{ color: tone }}>{disposition === "failed" ? "✕" : "✓"}</span>;
}

function pathOf(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

/** The origin a run is acting on, from the last step that named one. */
export function whereItIsActing(steps: RunStep[]): string | null {
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    const url = steps[index].url;
    if (!url) continue;
    try {
      return new URL(url).host;
    } catch {
      return url;
    }
  }
  return null;
}

export type { RunModel };
