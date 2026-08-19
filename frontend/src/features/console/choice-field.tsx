"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listChoices, skillKeys, type ParameterModel } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * A field that was a dropdown on the screen, kept as one here.
 *
 * Creating a supplier needs an address and a client, and neither is something a
 * person knows by heart — on the form they were lists, filled by calls, and the
 * operator picked. So this asks the target system what the options are, filters
 * them as somebody types, and hands back the id the call underneath needs while
 * showing the words a warehouse uses.
 *
 * Live on every open. A list of what existed when the task was taught is a way
 * of writing to a record that has since been deleted.
 */
export function ChoiceField({
  skillId,
  parameter,
  value,
  onPick,
}: {
  skillId: string;
  parameter: ParameterModel;
  value: string;
  onPick: (value: string) => void;
}) {
  const [typed, setTyped] = useState("");
  const [open, setOpen] = useState(false);
  const [debounced, setDebounced] = useState("");
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // The search goes to the warehouse's own endpoint; one call per keystroke
    // is a load test, not a search.
    const timer = setTimeout(() => setDebounced(typed.trim()), 250);
    return () => clearTimeout(timer);
  }, [typed]);

  useEffect(() => {
    const away = (event: MouseEvent) => {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    };
    // Escape as well as a click elsewhere: a list covering the Run button with
    // no way back is the reason this needed reporting.
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", escape);
    };
  }, []);

  const choices = useQuery({
    queryKey: skillKeys.choices(skillId, parameter.name, debounced),
    queryFn: () => listChoices(skillId, parameter.name, debounced),
    enabled: open,
    staleTime: 30_000,
  });

  const picked = useMemo(
    () => (choices.data ?? []).find((choice) => choice.value === value),
    [choices.data, value],
  );

  const failed =
    choices.error instanceof ApiError ? choices.error.problem.detail : choices.error ? String(choices.error) : null;

  return (
    <div ref={box} style={{ position: "relative", display: "flex", flexDirection: "column", gap: 4 }}>
      <input
        value={open ? typed : (picked?.label ?? value)}
        placeholder={`search ${parameter.name.replace(/_/g, " ")}`}
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setTyped(event.target.value);
          setOpen(true);
        }}
        style={{
          border: `1px solid ${ink.line}`,
          borderRadius: 7,
          padding: "7px 9px",
          fontSize: 12.5,
          fontFamily: value && !open ? mono : undefined,
          outline: "none",
        }}
      />
      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 20,
            marginTop: 4,
            maxHeight: 220,
            overflowY: "auto",
            // The wheel stays in the list. Without this, reaching the last row
            // hands the scroll to the conversation behind it and the options
            // slide off the screen mid-choice.
            overscrollBehavior: "contain",
            background: ink.panel,
            border: `1px solid ${ink.line}`,
            borderRadius: 8,
            boxShadow: "0 8px 24px rgba(0,0,0,0.10)",
          }}
        >
          {choices.isFetching && <Note>asking the system…</Note>}
          {/* A dropdown that is silently empty is the most misleading thing on a
              form: it looks like "nothing exists" and usually means "nobody is
              signed in". */}
          {failed && <Note>{failed}</Note>}
          {!choices.isFetching && !failed && (choices.data ?? []).length === 0 && (
            <Note>nothing matches {debounced ? `“${debounced}”` : "here"}</Note>
          )}
          {(choices.data ?? []).map((choice) => (
            <button
              key={choice.value}
              onClick={() => {
                onPick(choice.value);
                setOpen(false);
                setTyped("");
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "7px 10px",
                fontSize: 12,
                background: choice.value === value ? ink.infoWash : "transparent",
                border: "none",
                borderBottom: `1px solid ${ink.line}`,
                cursor: "pointer",
              }}
            >
              <span>{choice.label}</span>
              <span style={{ fontFamily: mono, fontSize: 10, color: ink.textMuted, marginLeft: 6 }}>
                {choice.value}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: "8px 10px", fontSize: 11.5, color: ink.textMuted }}>{children}</div>
  );
}
