"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { describeSkill, getSkill, skillKeys, type SkillVersionModel } from "@/features/skill/api";
import { getRun, runKeys, startRun, type RunModel } from "@/features/run/api";
import { runInThread, threadKeys } from "@/features/console/chat-api";
import { useRunStream } from "@/features/run/stream";
import { ApiError } from "@/lib/api/client";
import { whoAmI } from "@/lib/api/credential";
import { ChoiceField } from "@/features/console/choice-field";
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
  threadId,
  suggestions = [],
  folded = false,
  parameters,
  missing = [],
  onAsk,
  answeredBy,
}: {
  skillId: string;
  threadId?: string;
  suggestions?: string[];
  folded?: boolean;
  parameters?: Record<string, string>;
  missing?: string[];
  /** Put a sentence in the composer. What follows a result is the operator's
   * next question, so the suggestions write it rather than act on it. */
  onAsk?: (text: string) => void;
  /** A run that already answered this, made the moment the question was asked.
   * A read is safe and it is the whole point of asking, so it does not wait
   * behind a button — and what it shows is the system now, not what the
   * demonstration saw. */
  answeredBy?: string;
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
            PARAMETERS · {version.recording_ids.length === 1 ? "one run, nothing to diff" : "from the diff"}
          </div>
          <div style={{ fontFamily: mono, fontSize: 11.5, lineHeight: 1.9, color: "#3F4145" }}>
            {version.parameters.length === 0 && (
              <span style={{ color: ink.textMuted }}>
                {version.recording_ids.length === 1
                  ? "One demonstration, so nothing was diffed — every value is fixed as it was demonstrated."
                  : "Nothing varied between the runs — every value is fixed."}
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

      {/* The result gets the whole card. It shared a row with the provenance
          line before, which left a table of sixteen rows in half the width it
          needed while the other half said which recording it came from. */}
      <div
        style={{
          padding: "11px 16px",
          borderTop: `1px solid ${ink.lineSoft}`,
          fontSize: 12,
          color: ink.textSoft,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          minWidth: 0,
        }}
      >
        {parameters !== undefined && (
          <RunButton
            skillId={skillId}
            version={version}
            parameters={parameters}
            threadId={threadId}
            suggestions={suggestions}
            folded={folded}
            missing={missing}
            subject={skill.data.objective_key.entity_type.replace(/_/g, " ")}
            onAsk={onAsk}
            answeredBy={answeredBy}
          />
        )}
        <span style={{ fontSize: 11 }}>
          Provenance:{" "}
          <span style={{ fontFamily: mono, fontSize: 10.5 }}>
            {version.recording_ids.map((id) => id.slice(0, 10)).join(", ")}
          </span>{" "}
          · {version.induced_by}
        </span>
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
  threadId,
  suggestions = [],
  folded = false,
  version,
  parameters,
  missing,
  subject,
  onAsk,
  answeredBy,
}: {
  answeredBy?: string;
  subject: string;
  onAsk?: (text: string) => void;
  skillId: string;
  threadId?: string;
  suggestions?: string[];
  folded?: boolean;
  version: SkillVersionModel;
  parameters: Record<string, string>;
  missing: string[];
}) {
  const queryClient = useQueryClient();
  const [finished, setFinished] = useState<RunModel | null>(null);
  const [watching, setWatching] = useState<string | null>(null);
  const [given, setGiven] = useState<Record<string, string>>({});
  // A run in progress, step by step. The card shows what has happened so far
  // rather than a spinner over what might be happening.
  //
  // `still` matters on a reload: the message says a run started, the run is
  // not over, and rendering its stored row as a result read "It did not
  // finish" — which was a card describing a run that was still going.
  const [still, setStill] = useState(false);
  const streamed = useRunStream(watching ?? answeredBy, Boolean(watching) || still);
  // Already answered when the question was asked. Fetched rather than passed:
  // the reply is stored, and reopening the thread tomorrow should show what
  // the run found, not an empty card.
  const already = useQuery({
    queryKey: runKeys.detail(answeredBy ?? ""),
    queryFn: async () => {
      const run = await getRun(answeredBy as string);
      setStill(run.status === "running");
      return run;
    },
    enabled: Boolean(answeredBy) && !finished,
  });

  const run = useMutation({
    mutationFn: async () => {
      // Inside a conversation, the run is recorded there: the transcript is
      // what survives a re-render, a reload and tomorrow morning. Outside one
      // (the skills page), it is still just a run.
      if (threadId) {
        const thread = await runInThread(threadId, skillId, { ...parameters, ...given }, {
          version: version.version,
        });
        const last = thread.messages.at(-1)?.decision as { run_id?: string } | undefined;
        // Started, not finished: the card watches it happen from here.
        setWatching(last?.run_id ?? null);
        return null;
      }
      return startRun(
        skillId,
        { ...parameters, ...given },
        { authorizedBy: "confirmed", version: version.version },
      );
    },
    onSuccess: (started) => {
      if (started) setFinished(started);
      void queryClient.invalidateQueries({ queryKey: runKeys.all });
      void queryClient.invalidateQueries({ queryKey: threadKeys.all });
      if (!started) return;
      toast.success(`Run ${started.status}`, {
        // What was sent, not how many steps a demonstration had. Four of the
        // six are the operator's typing, which produces no call at L1 because
        // the WMS sends everything at Save — true, and it reads as though
        // two-thirds of the task did not happen.
        description:
          started.failure ??
          `${started.steps.filter((step) => step.disposition === "performed").length} calls, over ${started.medium}`,
      });
    },
    onError: (error) =>
      toast.error("The run did not start", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const settled = already.data?.status === "running" ? null : already.data;
  const done = finished ?? streamed.run ?? settled;
  if (done) {
    return (
      <Result
        run={done}
        subject={subject}
        onAsk={onAsk}
        suggestions={suggestions}
        folded={folded}
      />
    );
  }
  if (watching || still) {
    // Steps as they land, and whatever the row already had for a run that
    // started before this browser was looking.
    return <AsItHappens steps={streamed.steps.length ? streamed.steps : (already.data?.steps ?? [])} />;
  }

  // What it still needs, asked for here rather than in the next sentence. Chat
  // is the right shape for an open-ended request and the wrong one for four
  // fields with a known shape: a form collects them without ambiguity, and the
  // operator can see all of them at once instead of remembering which they
  // have already given.
  const plan = version.steps.find((step) => step.network_plan)?.network_plan ?? null;
  const wanted = version.parameters.filter((parameter) => parameter.kind === "input");
  const supplied = { ...parameters, ...given };
  const stillMissing = wanted
    .map((parameter) => parameter.name)
    .filter((name) => !supplied[name]?.trim());

  const blocked = stillMissing.length > 0 || version.stage === "recorded";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, width: "100%" }}>
      {missing.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {wanted.map((parameter) => (
            <label
              key={parameter.name}
              style={{ display: "flex", flexDirection: "column", gap: 4 }}
            >
              <span style={{ fontSize: 10.5, fontWeight: 700, color: ink.textMuted }}>
                {parameter.name.replace(/_/g, " ")}
              </span>
              {/* A field the screen offered as a list stays a list. Typing an
                  address id back from memory is not something anybody does. */}
              {parameter.options ? (
                <ChoiceField
                  skillId={skillId}
                  parameter={parameter}
                  value={supplied[parameter.name] ?? ""}
                  onPick={(value) => setGiven({ ...given, [parameter.name]: value })}
                />
              ) : (
                <input
                  value={supplied[parameter.name] ?? ""}
                  placeholder={parameter.observed_values[0] ?? ""}
                  onChange={(event) => setGiven({ ...given, [parameter.name]: event.target.value })}
                  style={{
                    border: `1px solid ${ink.line}`,
                    borderRadius: 7,
                    padding: "7px 9px",
                    fontSize: 12.5,
                    fontFamily: mono,
                    outline: "none",
                  }}
                />
              )}
              {parameter.description && (
                <span style={{ fontSize: 10.5, color: ink.textMuted }}>
                  {parameter.description}
                </span>
              )}
            </label>
          ))}
        </div>
      )}

      {/* What will actually be sent, before it is sent. An operator approving
          a write should be approving the request, not a sentence about it. */}
      {!blocked && plan && (
        <div
          style={{
            fontFamily: mono,
            fontSize: 11,
            color: ink.textSoft,
            background: ink.infoWash,
            borderRadius: 7,
            padding: "8px 10px",
            overflowX: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}
        >
          {`${plan.method} ${render(plan.url, supplied)}`}
          {plan.body ? `\n${render(plan.body, supplied)}` : ""}
        </div>
      )}

      <button
        onClick={() => run.mutate()}
        disabled={blocked || run.isPending}
        title={
          stillMissing.length > 0
            ? `Still needs ${stillMissing.join(", ")}`
            : version.stage === "recorded"
              ? "Nobody has reviewed this yet"
              : `Runs as ${whoAmI()?.principal ?? "whoever this token belongs to"}`
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
    </div>
  );
}

/** Fill a taught template with the values in hand, for the preview only. */
function render(template: string, values: Record<string, string>): string {
  return template.replace(/\$\{(\w+)\}/g, (whole, name: string) => values[name] ?? whole);
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
/**
 * A run while it is running.
 *
 * Every step appears as it completes, with what it called and what came back.
 * Twelve seconds of spinner and twelve seconds of watching calls land are the
 * same twelve seconds; only one of them tells you the system is working.
 */
function AsItHappens({ steps }: { steps: RunModel["steps"] }) {
  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 9,
        overflow: "hidden",
        background: ink.panel,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          background: ink.accentWash,
          borderBottom: `1px solid ${ink.lineSoft}`,
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: 999,
            background: ink.accent,
            animation: "sro-beat 1.1s ease-in-out infinite",
          }}
        />
        <span style={{ fontSize: 12, fontWeight: 700 }}>
          Running · {steps.length} step{steps.length === 1 ? "" : "s"} so far
        </span>
      </div>
      <ol style={{ margin: 0, padding: "8px 12px", listStyle: "none", display: "grid", gap: 4 }}>
        {steps.map((step) => (
          <li
            key={step.index}
            style={{
              display: "flex",
              gap: 8,
              alignItems: "baseline",
              fontFamily: mono,
              fontSize: 11,
              color: ink.textSoft,
              animation: "sro-land 220ms ease-out",
            }}
          >
            <Mark disposition={step.disposition} />
            <span style={{ color: ink.text }}>{step.method ?? "·"}</span>
            <span
              style={{
                flex: 1,
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {step.url ? new URL(step.url).pathname : step.intent}
            </span>
            {step.status_code !== null && <span>{step.status_code}</span>}
            {step.found_total !== null && step.found_total !== undefined && (
              <span style={{ color: ink.textMuted }}>{step.found_total} found</span>
            )}
          </li>
        ))}
        {steps.length === 0 && (
          <li style={{ fontSize: 11.5, color: ink.textMuted }}>Opening the connection…</li>
        )}
      </ol>
      <style>{`
        @keyframes sro-beat { 0%,100% { opacity: 1 } 50% { opacity: .35 } }
        @keyframes sro-land { from { opacity: 0; transform: translateY(-2px) } to { opacity: 1 } }
        @media (prefers-reduced-motion: reduce) { li, span { animation: none !important } }
      `}</style>
    </div>
  );
}

function Mark({ disposition }: { disposition: string }) {
  const colour =
    disposition === "performed"
      ? ink.goodDot
      : disposition === "failed"
        ? ink.danger
        : ink.textMuted;
  return <span style={{ color: colour, fontWeight: 700 }}>•</span>;
}


function Result({
  run,
  subject,
  onAsk,
  suggestions = [],
  folded = false,
}: {
  run: RunModel;
  subject: string;
  onAsk?: (text: string) => void;
  /** Earned by the backend from this answer's own columns and the skills
   * taught for this entity. Empty is a valid answer: no chips. */
  suggestions?: string[];
  /** An older turn in the transcript. Six copies of a 239-row table is a wall
   * nobody scrolls past; the answer is kept, the table waits to be asked for. */
  folded?: boolean;
  /** A run that already answered this, made the moment the question was asked.
   * A read is safe and it is the whole point of asking, so it does not wait
   * behind a button — and what it shows is the system now, not what the
   * demonstration saw. */
  answeredBy?: string;
}) {
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState(!folded);
  const perPage = 8;
  // The last step that found anything, not the first. A create opens by
  // reading the screen's policies, and showing that as the answer told an
  // operator who had just made a transport mode that three consolidation rules
  // were found. What a task did is what its last step did.
  const read = [...run.steps]
    .reverse()
    .find(
      (step) =>
        step.disposition === "performed" &&
        step.found_rows !== null &&
        step.found_rows !== undefined,
    );
  // Failed, not "not succeeded". A run still going is not a run that went
  // wrong, and treating it as one put "It did not finish" under a task that
  // was three seconds into finishing.
  const failed = run.status === "failed";
  // A rehearsal builds the write and holds it. Its last performed step is
  // whatever the screen read on the way in, and showing that as the result
  // told an operator who had just asked to create a transport mode that three
  // consolidation rules were found. A withheld write is the answer.
  const withheld = run.steps.find((step) => step.disposition === "withheld");

  if (failed) {
    // The step that actually failed, not the first one with anything to say. A
    // run whose seventh step could not run showed the second step's note --
    // "the demonstration produced no call here; only the UI moved" -- and sent
    // the operator looking at a UI step that was fine.
    const explained =
      run.steps.find(
        (step) => step.disposition === "failed" || (step.assertion_failures ?? []).length > 0,
      ) ?? run.steps.find((step) => step.detail);
    return (
      <span style={{ fontSize: 12.5, color: ink.danger }}>
        {run.failure ?? "It did not finish"}
        {explained?.detail && <span style={{ color: ink.textSoft }}> — {explained.detail}</span>}
      </span>
    );
  }

  if (withheld) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>Built, not sent</span>
        <span style={{ fontSize: 12, color: ink.textSoft }}>
          This is a rehearsal — the request was produced so it can be read before anything is
          changed. Run it again to send it.
        </span>
        <div
          style={{
            fontFamily: mono,
            fontSize: 11,
            background: ink.infoWash,
            borderRadius: 7,
            padding: "8px 10px",
            overflowX: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
          }}
        >
          {`${withheld.method ?? ""} ${withheld.url ?? ""}`.trim()}
        </div>
      </div>
    );
  }

  if (!read?.found_rows) {
    return <span style={{ fontSize: 12.5, color: ink.textSoft }}>Done.</span>;
  }

  if (!open) {
    const many = read.found_total ?? read.found_rows;
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          alignSelf: "flex-start",
          padding: "6px 10px",
          borderRadius: 7,
          border: `1px solid ${ink.line}`,
          background: ink.panel,
          fontSize: 12,
          color: ink.textSoft,
          cursor: "pointer",
        }}
      >
        <b style={{ color: ink.text }}>{many}</b> {subject} found · show
      </button>
    );
  }

  // The columns the result decided on, in its order. Never the row's own key
  // order: jsonb sorts an object's keys by length, so a row does not remember
  // how it was arranged.
  const columns = read.found_columns.length
    ? read.found_columns
    : Array.from(new Set(read.found.flatMap((row) => Object.keys(row))));
  const pages = Math.max(1, Math.ceil(read.found.length / perPage));
  // Clamped: a page number kept from a longer result would open on an empty
  // page, or on the last row of the new one, which reads as "1 found".
  const safePage = Math.min(page, pages - 1);
  const shown = read.found.slice(safePage * perPage, safePage * perPage + perPage);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", minWidth: 0 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
        {/* What exists, where the system said so — not what one page held.
            This number read 50 for a warehouse with 330,140 addresses. */}
        <span style={{ fontSize: 15, fontWeight: 700 }}>
          {read.found_partial ? `${read.found_rows}+` : (read.found_total ?? read.found_rows)}
        </span>
        <span style={{ fontSize: 12.5, color: ink.textSoft }}>
          {read.found_partial
            ? `at least — one page held ${read.found_rows}, and the system did not say how many there are`
            : "found"}
          {read.found.length < read.found_rows ? ` · ${read.found.length} carried back` : ""}
        </span>
        <span style={{ flex: 1 }} />
        {pages > 1 && (
          <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Step label="‹" onClick={() => setPage(safePage - 1)} disabled={safePage === 0} />
            <span style={{ fontSize: 11.5, color: ink.textMuted, fontFamily: mono }}>
              {safePage * perPage + 1}–{safePage * perPage + shown.length} of {read.found.length}
            </span>
            <Step
              label="›"
              onClick={() => setPage(safePage + 1)}
              disabled={safePage >= pages - 1}
            />
          </span>
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

      {onAsk && <NextActions suggestions={suggestions} onPick={onAsk} />}
    </div>
  );
}

function Step({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 6,
        background: "transparent",
        color: disabled ? ink.textMuted : ink.text,
        width: 22,
        height: 22,
        fontSize: 13,
        lineHeight: 1,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {label}
    </button>
  );
}

/**
 * What to do next, from what just happened.
 *
 * The suggestions come from the backend, which earns each one: a skill taught
 * for this entity, or a column in this very answer with few enough values to
 * be a category. They used to be three sentences written here — including
 * "which X are used for parcel", produced for one demo and then offered under
 * every result in the system, for entities where nothing could answer it.
 *
 * Offered as text the operator can edit rather than buttons that act, because
 * the sentence is still theirs.
 */
function NextActions({
  suggestions,
  onPick,
}: {
  suggestions: string[];
  onPick: (text: string) => void;
}) {
  if (suggestions.length === 0) return null;
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          onClick={() => onPick(suggestion)}
          style={{
            border: `1px solid ${ink.line}`,
            borderRadius: 999,
            background: "transparent",
            padding: "5px 11px",
            fontSize: 11.5,
            color: ink.textSoft,
            cursor: "pointer",
          }}
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
}
