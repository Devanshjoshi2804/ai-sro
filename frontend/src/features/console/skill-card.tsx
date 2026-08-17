"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { describeSkill, getSkill, skillKeys, type SkillVersionModel } from "@/features/skill/api";
import { runKeys, startRun, type RunModel } from "@/features/run/api";
import { ApiError } from "@/lib/api/client";
import { env } from "@/lib/env";
import { ink, mono } from "@/features/console/theme";

/**
 * The induced skill, in the thread.
 *
 * Everything here is read from the API — parameters with the values that proved
 * they vary, the assertions extracted from the demonstration, and which two
 * recordings it came from. Nothing is illustrative.
 */
export function SkillCard({
  skillId,
  parameters,
  missing = [],
}: {
  skillId: string;
  parameters?: Record<string, string>;
  missing?: string[];
}) {
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
        {parameters !== undefined && (
          <RunButton
            skillId={skillId}
            version={version}
            parameters={parameters}
            missing={missing}
          />
        )}
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

/**
 * Turning an offer into a run.
 *
 * The click *is* the authorisation: above shadow the backend refuses a run that
 * names nobody, so the operator who pressed this is the name on the record.
 * Disabled while a parameter is missing, because a half-supplied write is worse
 * than an unstarted one.
 */
function RunButton({
  skillId,
  version,
  parameters,
  missing,
}: {
  skillId: string;
  version: SkillVersionModel;
  parameters: Record<string, string>;
  missing: string[];
}) {
  const queryClient = useQueryClient();
  const [finished, setFinished] = useState<RunModel | null>(null);

  const run = useMutation({
    mutationFn: () =>
      startRun(skillId, parameters, {
        authorizedBy: env.NEXT_PUBLIC_PRINCIPAL_ID,
        version: version.version,
      }),
    onSuccess: (started) => {
      setFinished(started);
      void queryClient.invalidateQueries({ queryKey: runKeys.all });
      toast.success(`Run ${started.status}`, {
        description: started.failure ?? `${started.steps.length} steps, over ${started.medium}`,
      });
    },
    onError: (error) =>
      toast.error("The run did not start", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (finished) {
    return <Result run={finished} />;
  }

  const blocked = missing.length > 0 || version.stage === "recorded";
  return (
    <button
      onClick={() => run.mutate()}
      disabled={blocked || run.isPending}
      title={
        missing.length > 0
          ? `Still needs ${missing.join(", ")}`
          : version.stage === "recorded"
            ? "Nobody has reviewed this yet"
            : `Runs as ${env.NEXT_PUBLIC_PRINCIPAL_ID}`
      }
      style={{
        padding: "6px 12px",
        borderRadius: 7,
        border: "none",
        background: blocked ? "#E7E7E4" : ink.accent,
        color: blocked ? ink.textMuted : "#fff",
        fontSize: 12,
        fontWeight: 700,
        cursor: blocked ? "not-allowed" : "pointer",
      }}
    >
      {run.isPending ? "Running…" : "Run it"}
    </button>
  );
}

/**
 * What the run found, where the question was asked.
 *
 * A table rather than a paragraph, because the answer to "how many transport
 * modes" is sixteen rows with columns, and prose is where structure goes to
 * die. Sixteen fits; four thousand does not, so what is shown is a window onto
 * the result with the total said plainly above it — the row count is the
 * answer, the rows are the evidence, and the rest stays where it is rather than
 * being poured through a chat message.
 */
function Result({ run }: { run: RunModel }) {
  const [expanded, setExpanded] = useState(false);
  const read = run.steps.find((step) => step.found_rows !== null && step.found_rows !== undefined);
  const failed = run.status !== "succeeded";

  if (failed) {
    const explained = run.steps.find((step) => step.detail);
    return (
      <span style={{ fontSize: 12.5, color: ink.danger }}>
        {run.failure ?? "It did not finish"}
        {explained?.detail && <span style={{ color: ink.textSoft }}> — {explained.detail}</span>}
      </span>
    );
  }

  if (!read?.found_rows) {
    return <span style={{ fontSize: 12.5, color: ink.textSoft }}>Done.</span>;
  }

  // Every column any sampled row declares, in the order the ranking put them.
  const columns = Array.from(new Set(read.found.flatMap((row) => Object.keys(row))));
  const shown = expanded ? read.found : read.found.slice(0, 5);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 15, fontWeight: 700 }}>{read.found_rows}</span>
        <span style={{ fontSize: 12.5, color: ink.textSoft }}>
          found{read.found.length < read.found_rows ? `, showing ${shown.length}` : ""}
        </span>
        <span style={{ flex: 1 }} />
        {read.found.length > 5 && (
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              border: "none",
              background: "transparent",
              color: ink.accentDeep,
              fontSize: 12,
              fontWeight: 700,
              cursor: "pointer",
              padding: 0,
            }}
          >
            {expanded ? "Show less" : `Show all ${read.found.length}`}
          </button>
        )}
      </div>

      {/* Its own scroll container: a wide result must never make the whole
          conversation scroll sideways. */}
      <div style={{ overflowX: "auto", border: `1px solid ${ink.line}`, borderRadius: 8 }}>
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12.5 }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  style={{
                    textAlign: "left",
                    padding: "7px 10px",
                    borderBottom: `1px solid ${ink.line}`,
                    color: ink.textMuted,
                    fontSize: 10.5,
                    fontWeight: 700,
                    letterSpacing: ".04em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  {column.replace(/([a-z])([A-Z])/g, "$1 $2")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => (
              <tr
                key={index}
                style={{ borderTop: index ? `1px solid ${ink.lineSoft}` : undefined }}
              >
                {columns.map((column) => (
                  <td
                    key={column}
                    style={{
                      padding: "7px 10px",
                      fontFamily: mono,
                      whiteSpace: "nowrap",
                      color: row[column] ? ink.text : ink.textMuted,
                    }}
                  >
                    {row[column] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
