"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import {
  describeSkill,
  getSkill,
  skillKeys,
  type SkillVersionModel,
} from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * The induced skill, in the thread.
 *
 * Everything here is read from the API — parameters with the values that proved
 * they vary, the assertions extracted from the demonstration, and which two
 * recordings it came from. Nothing is illustrative.
 */
export function SkillCard({ skillId }: { skillId: string }) {
  const [open, setOpen] = useState(false);
  const skill = useQuery({ queryKey: skillKeys.detail(skillId), queryFn: () => getSkill(skillId) });

  if (!skill.data) return null;
  const version = skill.data.versions.at(-1);
  if (!version) return null;

  const step = version.steps[0];
  const headers = step?.network_plan?.headers ?? {};
  const credentials = Object.entries(headers).filter(
    ([, value]) => value.startsWith("<") && value.includes("/"),
  );
  const minted = Object.entries(headers).filter(([, value]) => value === "<minted per run>");

  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 12,
        background: ink.panel,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "14px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: `1px solid ${ink.lineSoft}`,
        }}
      >
        <span style={{ fontSize: 14.5, fontWeight: 700 }}>{skill.data.name}</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: ink.textMuted }}>
          v{version.version} · {skill.data.objective_key.target_system} ·{" "}
          {skill.data.objective_key.facility}
        </span>
        <span style={{ flex: 1 }} />
        <span
          style={{
            fontSize: 9.5,
            fontWeight: 700,
            letterSpacing: ".05em",
            padding: "3px 7px",
            borderRadius: 4,
            background: ink.infoWash,
            color: ink.info,
            textTransform: "uppercase",
          }}
        >
          {version.stage}
        </span>
      </div>

      <Description skillId={skillId} version={version} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        <div
          style={{
            padding: "14px 16px",
            borderRight: `1px solid ${ink.lineSoft}`,
            display: "flex",
            flexDirection: "column",
            gap: 9,
          }}
        >
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              letterSpacing: ".08em",
              color: ink.textMuted,
            }}
          >
            PARAMETERS · from the diff
          </div>
          <div style={{ fontFamily: mono, fontSize: 11.5, lineHeight: 1.9, color: "#3F4145" }}>
            {version.parameters.length === 0 && (
              <span style={{ color: ink.textMuted }}>
                Nothing varied between the runs — every value is fixed.
              </span>
            )}
            {version.parameters.map((parameter) => (
              <div key={parameter.name}>
                <span style={{ color: ink.accentDeep }}>${parameter.name}</span>{" "}
                <span style={{ color: ink.textSoft }}>{parameter.observed_values.join(" · ")}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 9 }}>
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 700,
              letterSpacing: ".08em",
              color: ink.textMuted,
            }}
          >
            VERIFICATION
          </div>
          <div style={{ fontSize: 12, lineHeight: 1.9, color: "#3F4145" }}>
            {step?.assertions.length === 0 && (
              <span style={{ color: ink.textMuted }}>No assertions extracted.</span>
            )}
            {step?.assertions.map((assertion, index) => (
              <div key={index}>
                {assertion.kind}{" "}
                <span style={{ fontFamily: mono }}>
                  {assertion.pointer ? `${assertion.pointer} == ` : ""}
                  {assertion.expected}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={() => setOpen((value) => !value)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "10px 16px",
          borderTop: `1px solid ${ink.lineSoft}`,
          border: "none",
          borderTopWidth: 1,
          borderTopStyle: "solid",
          borderTopColor: ink.lineSoft,
          fontSize: 12,
          fontWeight: 600,
          color: ink.textSoft,
          cursor: "pointer",
          background: "#FBFBFA",
        }}
      >
        {open ? "▾" : "▸"} {open ? "Hide the plan" : "How this will be performed"}
      </button>

      {open && step && (
        <div
          style={{
            padding: "14px 16px",
            borderTop: `1px solid ${ink.lineSoft}`,
            background: ink.bar,
            fontFamily: mono,
            fontSize: 11.5,
            lineHeight: 1.95,
            color: "#C9CACB",
            whiteSpace: "pre-wrap",
            overflow: "auto",
          }}
        >
          {step.network_plan
            ? [
                `L1  ${step.network_plan.method} ${step.network_plan.url}`,
                step.network_plan.body ? `    body ${step.network_plan.body}` : null,
                credentials.length
                  ? `    credentials ${credentials.map(([name]) => name).join(", ")} → vault`
                  : null,
                minted.length ? `    minted ${minted.map(([name]) => name).join(", ")}` : null,
                !step.network_plan.replayable
                  ? `    NOT REPLAYABLE · ${step.network_plan.unreplayable_reason}`
                  : null,
              ]
                .filter(Boolean)
                .join("\n")
            : "L1  no network plan — this step is UI only"}
          {step.ui_plan
            ? `\nL2  ${step.ui_plan.action} ${step.ui_plan.target_path ?? step.ui_plan.target ?? ""}`
            : ""}
          {`\nL3  vision, using the demonstration as the reference for done`}
        </div>
      )}

      <div
        style={{
          padding: "11px 16px",
          borderTop: `1px solid ${ink.lineSoft}`,
          fontSize: 12,
          color: ink.textSoft,
          display: "flex",
          gap: 8,
          alignItems: "center",
        }}
      >
        <span>
          Provenance:{" "}
          <span style={{ fontFamily: mono, fontSize: 11 }}>
            {version.recording_ids.map((id) => id.slice(0, 10)).join(", ")}
          </span>{" "}
          · {version.induced_by}
        </span>
        <span style={{ flex: 1 }} />
        <Link href={`/skills/${skillId}`} style={{ color: ink.accentDeep, fontWeight: 600 }}>
          Review and promote →
        </Link>
      </div>
    </div>
  );
}

/**
 * What the skill is for, and the one place it can be corrected.
 *
 * Induction writes this from the evidence — the objective, the call it writes
 * with, the parameters the diff found, and the operator's own closing sentence
 * where they narrated. It is editable because it is what a spoken request will
 * be matched against later: a skill described in words nobody uses is a skill
 * nobody finds. Editing changes what finds it, never what it does.
 */
function Description({ skillId, version }: { skillId: string; version: SkillVersionModel }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [summary, setSummary] = useState(version.summary);
  const [whenToUse, setWhenToUse] = useState(version.when_to_use);

  const save = useMutation({
    mutationFn: () => describeSkill(skillId, version.version, summary.trim(), whenToUse.trim()),
    onSuccess: () => {
      setEditing(false);
      void queryClient.invalidateQueries({ queryKey: skillKeys.detail(skillId) });
      void queryClient.invalidateQueries({ queryKey: skillKeys.all });
    },
    onError: (error) =>
      toast.error("Could not save the description", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (!version.summary && !editing) return null;

  return (
    <div
      style={{
        padding: "13px 16px",
        borderBottom: `1px solid ${ink.lineSoft}`,
        display: "flex",
        flexDirection: "column",
        gap: 7,
      }}
    >
      {editing ? (
        <>
          <textarea
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
            rows={2}
            style={inputStyle}
          />
          <textarea
            value={whenToUse}
            onChange={(event) => setWhenToUse(event.target.value)}
            rows={2}
            placeholder="When to use it"
            style={inputStyle}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => save.mutate()}
              disabled={!summary.trim() || save.isPending}
              style={{
                padding: "6px 12px",
                borderRadius: 7,
                border: "none",
                background: ink.accent,
                color: "#fff",
                fontSize: 12,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              {save.isPending ? "Saving…" : "Save"}
            </button>
            <button
              onClick={() => setEditing(false)}
              style={{
                padding: "6px 12px",
                borderRadius: 7,
                border: "none",
                background: "transparent",
                color: ink.textSoft,
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 13, lineHeight: 1.65 }}>{version.summary}</div>
          {version.when_to_use && (
            <div style={{ fontSize: 12, color: ink.textSoft, lineHeight: 1.6 }}>
              {version.when_to_use}
            </div>
          )}
          <button
            onClick={() => setEditing(true)}
            style={{
              alignSelf: "flex-start",
              border: "none",
              background: "transparent",
              padding: 0,
              fontSize: 11.5,
              fontWeight: 600,
              color: ink.textMuted,
              cursor: "pointer",
            }}
          >
            Say it in your words
          </button>
        </>
      )}
    </div>
  );
}

const inputStyle = {
  border: `1px solid ${ink.line}`,
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 12.5,
  lineHeight: 1.6,
  resize: "vertical",
  fontFamily: "inherit",
  background: "#fff",
  color: ink.text,
} as const;
