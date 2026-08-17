"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  listRecordings,
  recordingKeys,
  startRecording,
  type ObjectiveKey,
  type StartRecordingRequest,
} from "@/features/recording/api";
import { induceSkill, listSkills, skillKeys } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";
import { BatchCard } from "@/features/console/batch-card";
import { SkillCard } from "@/features/console/skill-card";
import { TeachPanel } from "@/features/console/teach-panel";
import { useThread } from "@/features/console/thread-store";
import { TopBar } from "@/features/console/top-bar";
import {
  ConnectPanel,
  checkSessions,
  connectionKeys,
  listConnections,
  signInAgain,
  type SessionCheck,
} from "@/features/console/connect-panel";
import {
  getThread,
  say,
  startThread,
  threadKeys,
  type ChatMessage,
} from "@/features/console/chat-api";

/**
 * A teaching session is started by naming a URL and nothing else.
 *
 * What the task *is* — its objective key — is read off the evidence when the
 * run is sealed: the call the demonstration ended on names the entity and the
 * verb, the parameter every call carried names the facility. Asking the
 * operator to type all five up front produced pairs that never matched, because
 * two people describe one task two ways and the diff needs exact equality.
 *
 * Run 2 is then started under run 1's derived name, so the pair is guaranteed
 * to pair.
 */
type Teaching = {
  start_url: string;
  objective_key: ObjectiveKey | null;
};

export function Console() {
  const queryClient = useQueryClient();
  const thread = useThread();

  const [tab, setTab] = useState<"chat" | "teach">("chat");
  const [plusOpen, setPlusOpen] = useState(false);
  const [teachingAt, setTeachingAt] = useState<Teaching | null>(null);
  const [active, setActive] = useState<{ recordingId: string; run: number } | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const skills = useQuery({ queryKey: skillKeys.all, queryFn: listSkills });
  const connections = useQuery({ queryKey: connectionKeys.all, queryFn: listConnections });
  // Asked of the systems themselves, and asked again while the console is open:
  // a session dies on the system's schedule, not on ours, and the whole point is
  // to say so before a demonstration walks into a login page.
  const health = useQuery({
    queryKey: connectionKeys.health,
    queryFn: checkSessions,
    refetchInterval: 60_000,
    enabled: (connections.data ?? []).length > 0,
  });
  const recordings = useQuery({ queryKey: recordingKeys.all, queryFn: listRecordings });

  // The conversation lives server-side: a reload used to lose it, and what was
  // asked and what the system decided are half of the audit trail.
  const conversation = useQuery({
    queryKey: threadKeys.detail(threadId ?? ""),
    queryFn: () => getThread(threadId as string),
    enabled: threadId !== null,
  });

  const ask = useMutation({
    mutationFn: async (text: string) => {
      const id = threadId ?? (await startThread()).id;
      if (threadId === null) setThreadId(id);
      return say(id, text);
    },
    onSuccess: (updated) => {
      setDraft("");
      queryClient.setQueryData(threadKeys.detail(updated.id), updated);
      void queryClient.invalidateQueries({ queryKey: threadKeys.all });
    },
    onError: (error) =>
      toast.error("Could not send that", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const start = useMutation({
    mutationFn: ({ form, run }: { form: Teaching; run: number }) => {
      const body: StartRecordingRequest = {
        objective_key: form.objective_key,
        start_url: form.start_url.trim() || null,
        label: `run ${run}`,
      };
      return startRecording(body);
    },
    onSuccess: (started, variables) => {
      thread.add({
        kind: "session",
        recordingId: started.recording_id,
        run: variables.run,
        label: variables.form.objective_key?.objective_type ?? variables.form.start_url,
      });
      setActive({ recordingId: started.recording_id, run: variables.run });
      setTab("teach");
      void queryClient.invalidateQueries({ queryKey: recordingKeys.all });
    },
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      // The one-session hint is only true when the browser is what refused.
      // Appending it to every failure sent an operator looking at Steel while
      // the actual answer — a request the API would not accept — was on screen.
      const busy = error instanceof ApiError && error.problem.status === 503;
      thread.add({
        kind: "system",
        text:
          `Could not open a browser session: ${detail}` +
          (busy
            ? ". The browser may already be in use — a self-hosted Steel runs one session at a time."
            : ""),
      });
      toast.error("Could not open a browser session", { description: detail });
    },
  });

  const induce = useMutation({
    mutationFn: ([first, second]: [string, string]) => induceSkill(first, second),
    onSuccess: (result) => {
      thread.add({ kind: "skill", skillId: result.skill_id, version: result.version });
      void queryClient.invalidateQueries({ queryKey: skillKeys.all });
    },
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      thread.add({ kind: "system", text: `Induction refused: ${detail}` });
      toast.error("Induction refused", { description: detail });
    },
  });

  const beginTeaching = (startUrl: string) => {
    const form: Teaching = { start_url: startUrl, objective_key: null };
    setTeachingAt(form);
    thread.add({ kind: "operator", text: `Teach a workflow at ${startUrl}` });
    start.mutate({ form, run: 1 });
  };

  const onSealed = (frames: number, objectiveKey: ObjectiveKey | null) => {
    if (!active) return;
    thread.add({ kind: "sealed", recordingId: active.recordingId, run: active.run, frames });
    setActive(null);
    setTab("chat");

    // Run 1's derived name becomes run 2's, so the pair pairs.
    if (teachingAt && objectiveKey) setTeachingAt({ ...teachingAt, objective_key: objectiveKey });

    const sealed = [...thread.sealedRecordings, active.recordingId];
    if (sealed.length >= 2 && teachingAt) {
      const pair = sealed.slice(-2) as [string, string];
      induce.mutate(pair);
    }
  };

  const runsSoFar = thread.sealedRecordings.length;
  const teaching = active !== null;

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        fontFamily: "Manrope, var(--font-geist-sans), sans-serif",
        color: ink.text,
        background: ink.page,
        overflow: "hidden",
      }}
    >
      <TopBar>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 4 }}>
          <Tab active={tab === "chat"} onClick={() => setTab("chat")} dot="#5A5C60">
            Threads
          </Tab>
          {teaching && (
            <Tab active={tab === "teach"} onClick={() => setTab("teach")} dot={ink.danger} pulse>
              Teaching session
            </Tab>
          )}
        </div>
      </TopBar>

      {connecting ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <ConnectPanel onDone={() => setConnecting(false)} />
        </div>
      ) : tab === "teach" && active ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <TeachPanel
            recordingId={active.recordingId}
            run={active.run}
            objectiveKey={teachingAt?.objective_key}
            onSealed={onSealed}
            onDiscarded={() => {
              setActive(null);
              setTab("chat");
              thread.add({ kind: "system", text: "Run discarded. Nothing was learned from it." });
            }}
          />
        </div>
      ) : (
        <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
          <aside
            style={{
              width: 236,
              flex: "0 0 236px",
              borderRight: `1px solid ${ink.line}`,
              background: ink.panel,
              padding: "16px 12px",
              display: "flex",
              flexDirection: "column",
              gap: 22,
              overflow: "auto",
            }}
          >
            <Section title="SYSTEMS">
              {(connections.data ?? []).map((connection) => (
                <div
                  key={connection.id}
                  style={{
                    padding: "9px 10px",
                    border: `1px solid ${ink.line}`,
                    borderRadius: 8,
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                  }}
                >
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>{connection.name}</span>
                  <SessionState
                    check={(health.data ?? []).find((c) => c.connection_id === connection.id)}
                    status={connection.status}
                    connection={connection}
                    onReconnect={() => setConnecting(true)}
                  />
                </div>
              ))}
              {(connections.data ?? []).length === 0 && (
                <button
                  onClick={() => setConnecting(true)}
                  style={{
                    padding: "9px 10px",
                    fontSize: 12.5,
                    color: ink.textMuted,
                    background: "transparent",
                    border: `1px dashed ${ink.line}`,
                    borderRadius: 8,
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  None connected — add one
                </button>
              )}
            </Section>

            <Section title="SKILLS">
              {(skills.data ?? []).map((skill) => (
                <Link
                  key={skill.id}
                  href={`/skills/${skill.id}`}
                  style={{
                    padding: "9px 10px",
                    border: `1px solid ${ink.line}`,
                    borderRadius: 8,
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    color: ink.text,
                  }}
                >
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>
                    {skill.name}{" "}
                    <span style={{ color: ink.textMuted, fontWeight: 500 }}>
                      v{skill.latest_version}
                    </span>
                  </span>
                  <span
                    style={{
                      fontSize: 9.5,
                      fontWeight: 700,
                      letterSpacing: ".05em",
                      padding: "2px 6px",
                      borderRadius: 4,
                      background: ink.infoWash,
                      color: ink.info,
                      alignSelf: "flex-start",
                      textTransform: "uppercase",
                    }}
                  >
                    {skill.latest_stage}
                  </span>
                </Link>
              ))}
              {(skills.data ?? []).length === 0 && (
                <span style={{ padding: "9px 10px", fontSize: 12.5, color: ink.textMuted }}>
                  None yet — teach one from the + menu
                </span>
              )}
            </Section>

            <Section title="RECENT SESSIONS">
              {(recordings.data ?? []).slice(0, 6).map((recording) => (
                <Link
                  key={recording.id}
                  href={`/recordings/${recording.id}`}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 8,
                    fontSize: 12.5,
                    color: ink.textSoft,
                    display: "flex",
                    gap: 7,
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      background:
                        recording.status === "sealed"
                          ? ink.goodDot
                          : recording.status === "capturing"
                            ? ink.accent
                            : ink.textMuted,
                    }}
                  />
                  {recording.objective_key?.objective_type ?? "unnamed"}
                  <span style={{ color: ink.textMuted, fontSize: 11 }}>
                    {recording.frame_count}
                  </span>
                </Link>
              ))}
            </Section>

            <span style={{ flex: 1 }} />
            <div
              style={{
                borderTop: `1px solid ${ink.lineSoft}`,
                padding: "12px 8px 0",
                fontSize: 11,
                lineHeight: 1.6,
                color: ink.textMuted,
              }}
            >
              Capture stays inside your infrastructure. Secrets are stored as vault references only.
            </div>
          </aside>

          <main
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              minWidth: 0,
              minHeight: 0,
            }}
          >
            <div style={{ flex: 1, overflow: "auto", padding: "34px 0 20px" }}>
              <div
                style={{
                  maxWidth: 772,
                  margin: "0 auto",
                  padding: "0 28px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 20,
                }}
              >
                <Assistant>
                  Ask me for a task and I will tell you which taught skill does it, and what it
                  still needs. If nothing has been taught for it, I will say what the knowledge base
                  knows — and you can teach me by doing it twice.
                </Assistant>

                {(conversation.data?.messages ?? []).map((message) => (
                  <ChatTurn key={message.id} message={message} />
                ))}

                {ask.isPending && <Assistant>Looking through what has been taught…</Assistant>}

                {thread.entries.map((entry) => {
                  switch (entry.kind) {
                    case "operator":
                      return <Operator key={entry.id}>{entry.text}</Operator>;
                    case "system":
                      return <Assistant key={entry.id}>{entry.text}</Assistant>;
                    case "session":
                      return (
                        <Assistant key={entry.id}>
                          Run {entry.run} open. Do the task exactly as you normally would — every
                          gesture, call and accessibility tree is being captured.
                        </Assistant>
                      );
                    case "sealed":
                      return (
                        <Assistant key={entry.id}>
                          Run {entry.run} sealed with {entry.frames} step
                          {entry.frames === 1 ? "" : "s"}.{" "}
                          {entry.run === 1
                            ? "Do it once more with different values so the diff can find the parameters."
                            : "Both runs captured."}
                        </Assistant>
                      );
                    case "skill":
                      return (
                        <div key={entry.id} style={{ display: "flex", gap: 12 }}>
                          <Avatar />
                          <div
                            style={{
                              flex: 1,
                              minWidth: 0,
                              display: "flex",
                              flexDirection: "column",
                              gap: 12,
                            }}
                          >
                            <div style={{ fontSize: 15, lineHeight: 1.6 }}>
                              Two demonstrations aligned and diffed. What changed became a
                              parameter, what held stayed literal. No model was asked what the
                              parameters are.
                            </div>
                            <SkillCard skillId={entry.skillId} />
                          </div>
                        </div>
                      );
                  }
                })}

                {induce.isPending && (
                  <Assistant>Aligning the two runs and diffing the replayable values…</Assistant>
                )}

                {teachingAt && !teaching && runsSoFar !== 2 && (
                  <div style={{ display: "flex", gap: 12 }}>
                    <Avatar />
                    <button
                      onClick={() =>
                        start.mutate({ form: teachingAt, run: runsSoFar === 1 ? 2 : 1 })
                      }
                      disabled={start.isPending}
                      style={{
                        padding: "10px 16px",
                        borderRadius: 8,
                        background: ink.accent,
                        color: "#fff",
                        border: "none",
                        fontSize: 13,
                        fontWeight: 700,
                        cursor: "pointer",
                        alignSelf: "flex-start",
                      }}
                    >
                      {start.isPending
                        ? "Opening…"
                        : runsSoFar === 1
                          ? "Start run 2"
                          : "Try opening a session again"}
                    </button>
                  </div>
                )}

                {teachingAt === null && (
                  <TeachForm onStart={beginTeaching} pending={start.isPending} />
                )}
              </div>
            </div>

            <div style={{ flex: "0 0 auto", padding: "0 28px 24px" }}>
              <div style={{ maxWidth: 772, margin: "0 auto", position: "relative" }}>
                {plusOpen && (
                  <div
                    style={{
                      position: "absolute",
                      bottom: 74,
                      left: 0,
                      width: 288,
                      background: ink.panel,
                      border: `1px solid ${ink.line}`,
                      borderRadius: 12,
                      boxShadow: "0 12px 32px rgba(20,20,20,.13)",
                      padding: 6,
                      zIndex: 5,
                    }}
                  >
                    <PlusItem
                      icon="◉"
                      title="Teach a workflow"
                      subtitle="Opens a recorded browser session"
                      onClick={() => {
                        setPlusOpen(false);
                        setTeachingAt(null);
                        document
                          .getElementById("teach-form")
                          ?.scrollIntoView({ behavior: "smooth" });
                      }}
                    />
                    <PlusItem
                      icon="▤"
                      title="Attach knowledge base"
                      subtitle="Not built yet — phase 4"
                      disabled
                    />
                    <PlusItem
                      icon="⌗"
                      title="Connect a system"
                      subtitle="You sign in there; the session is kept encrypted"
                      onClick={() => {
                        setPlusOpen(false);
                        setConnecting(true);
                      }}
                    />
                  </div>
                )}

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    background: ink.panel,
                    border: `1px solid ${ink.line}`,
                    borderRadius: 14,
                    padding: "9px 12px 9px 10px",
                  }}
                >
                  <button
                    onClick={() => setPlusOpen((value) => !value)}
                    style={{
                      width: 32,
                      height: 32,
                      flex: "0 0 32px",
                      borderRadius: 9,
                      background: ink.page,
                      border: "none",
                      display: "grid",
                      placeItems: "center",
                      fontSize: 19,
                      color: ink.textSoft,
                      cursor: "pointer",
                    }}
                  >
                    +
                  </button>
                  <input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && draft.trim() && !ask.isPending) {
                        ask.mutate(draft.trim());
                      }
                    }}
                    placeholder="Ask for a task — or teach one with +"
                    style={{
                      flex: 1,
                      border: "none",
                      outline: "none",
                      fontSize: 14.5,
                      background: "transparent",
                      color: ink.text,
                    }}
                  />
                </div>
                <div style={{ padding: "9px 4px 0", fontSize: 11, color: ink.textMuted }}>
                  Asking finds a taught skill and says what it still needs. Running it is a separate
                  click — that confirmation is what an assisted run records as its authorisation.
                </div>
              </div>
            </div>
          </main>
        </div>
      )}
    </div>
  );
}

function TeachForm({
  onStart,
  pending,
}: {
  onStart: (startUrl: string) => void;
  pending: boolean;
}) {
  const [url, setUrl] = useState("");
  const ready = url.trim().length > 0;

  return (
    <div id="teach-form" style={{ display: "flex", gap: 12 }}>
      <Avatar />
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
        <div style={{ fontSize: 14, fontWeight: 700 }}>Where does this task start?</div>
        <div style={{ fontSize: 12.5, color: ink.textSoft, lineHeight: 1.6 }}>
          Paste the screen you would open to do it. Nothing else is asked: what the task is gets
          read off what it does — the call it ends on names the entity and the action.
        </div>
        <Field
          label="Start URL"
          placeholder="https://wms.acme-dc.internal/inventory"
          value={url}
          onChange={setUrl}
        />
        <button
          onClick={() => onStart(url.trim())}
          disabled={!ready || pending}
          style={{
            alignSelf: "flex-start",
            padding: "10px 16px",
            borderRadius: 8,
            border: "none",
            background: ready ? ink.accent : "#E7E7E4",
            color: ready ? "#fff" : ink.textMuted,
            fontSize: 13,
            fontWeight: 700,
            cursor: ready ? "pointer" : "not-allowed",
          }}
        >
          {pending ? "Opening a browser…" : "Open a session and start run 1"}
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <span style={{ fontSize: 11, fontWeight: 700, color: ink.textMuted }}>{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
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
  );
}

function Tab({
  children,
  active,
  onClick,
  dot,
  pulse,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
  dot: string;
  pulse?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 16px",
        height: 34,
        borderRadius: "8px 8px 0 0",
        border: "none",
        fontSize: 12.5,
        fontWeight: 600,
        cursor: "pointer",
        background: active ? ink.page : "transparent",
        color: active ? ink.text : "#8A8C8F",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: dot,
          animation: pulse ? "recpulse 1.4s infinite" : undefined,
        }}
      />
      {children}
    </button>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          letterSpacing: ".08em",
          color: ink.textMuted,
          padding: "0 8px 4px",
        }}
      >
        {title}
      </div>
      {children}
    </div>
  );
}

function Avatar() {
  return (
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
  );
}

function Assistant({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      <Avatar />
      <div style={{ paddingTop: 3, fontSize: 15, lineHeight: 1.6, maxWidth: "56ch" }}>
        {children}
      </div>
    </div>
  );
}

function Operator({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        alignSelf: "flex-end",
        maxWidth: "60%",
        background: ink.text,
        color: "#F2F2F0",
        padding: "11px 15px",
        borderRadius: "14px 14px 4px 14px",
        fontSize: 14.5,
      }}
    >
      {children}
    </div>
  );
}

function PlusItem({
  icon,
  title,
  subtitle,
  onClick,
  disabled,
}: {
  icon: string;
  title: string;
  subtitle: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: "flex",
        gap: 11,
        alignItems: "flex-start",
        padding: "10px 11px",
        borderRadius: 8,
        border: "none",
        background: "transparent",
        width: "100%",
        textAlign: "left",
        cursor: disabled ? "default" : "pointer",
        opacity: disabled ? 0.45 : 1,
      }}
    >
      <span
        style={{
          width: 24,
          height: 24,
          flex: "0 0 24px",
          borderRadius: 6,
          background: disabled ? "#F1F1EE" : ink.accentWash,
          color: disabled ? ink.textSoft : ink.accentDeep,
          display: "grid",
          placeItems: "center",
          fontSize: 13,
          fontWeight: 800,
        }}
      >
        {icon}
      </span>
      <span>
        <span style={{ display: "block", fontSize: 13, fontWeight: 700 }}>{title}</span>
        <span style={{ display: "block", fontSize: 11.5, color: "#7A7C7F", lineHeight: 1.5 }}>
          {subtitle}
        </span>
      </span>
    </button>
  );
}

/**
 * One turn of the conversation.
 *
 * The decision is rendered beside the prose, not instead of it: an operator
 * reads the sentence, and anybody asking "why did it pick that" reads what
 * matched. A skill that was found is offered with its card — running it stays a
 * separate, deliberate click.
 */
function ChatTurn({ message }: { message: ChatMessage }) {
  if (message.speaker === "operator") return <Operator>{message.text}</Operator>;

  const decision = message.decision as {
    matched_skill_id?: string | null;
    matched_version?: number | null;
    confident?: boolean;
    runnable?: boolean;
    missing_parameters?: string[];
    why?: string[];
    proposal_sources?: string[];
    items?: Record<string, string>[];
    note?: string;
  };
  const items = decision.items ?? [];

  return (
    <div style={{ display: "flex", gap: 12 }}>
      <Avatar />
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 15, lineHeight: 1.65, whiteSpace: "pre-wrap" }}>{message.text}</div>

        {decision.why && decision.why.length > 0 && (
          <div style={{ fontFamily: mono, fontSize: 11, color: ink.textMuted }}>
            matched on {decision.why.join(" · ")}
            {decision.confident === false && " — and something in the sentence it cannot explain"}
          </div>
        )}

        {decision.proposal_sources && decision.proposal_sources.length > 0 && (
          <div style={{ fontFamily: mono, fontSize: 11, color: ink.textMuted }}>
            from {decision.proposal_sources.join(", ")}
          </div>
        )}

        {decision.note && <div style={{ fontSize: 12, color: ink.textSoft }}>{decision.note}</div>}

        {decision.matched_skill_id && items.length > 0 && (
          <BatchCard
            skillId={decision.matched_skill_id}
            skillName={`v${decision.matched_version ?? 1}`}
            items={items}
            runnable={decision.runnable !== false}
          />
        )}

        {decision.matched_skill_id && (
          <SkillCard
            skillId={decision.matched_skill_id}
            parameters={items.length === 1 ? items[0] : {}}
            missing={items.length ? [] : (decision.missing_parameters ?? [])}
          />
        )}
      </div>
    </div>
  );
}

/**
 * What the stored session is actually worth, right now.
 *
 * The row used to read "session held" whenever the database said connected,
 * which stayed true for weeks after the system had forgotten the session. An
 * operator only found out by being shown a login page inside a demonstration.
 * Now a dead session says so here, with the one action that fixes it.
 */
function SessionState({
  check,
  status,
  connection,
  onReconnect,
}: {
  check?: SessionCheck;
  status: string;
  connection: { id: string; target_system: string };
  onReconnect: () => void;
}) {
  const queryClient = useQueryClient();
  // Tried first, because a connection that holds credentials should never make
  // anybody type them a second time. Only when there are none does the operator
  // get the login page.
  const retry = useMutation({
    mutationFn: () => signInAgain(connection.id, connection.target_system),
    onSuccess: () => {
      toast.success("Signed back in", { description: "Nobody had to be asked." });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
    },
    onError: onReconnect,
  });
  const state = check?.health ?? (status === "connected" ? "checking" : "never_connected");
  const { dot, label } = {
    signed_in: { dot: ink.goodDot, label: "signed in" },
    signed_out: { dot: "#C0392B", label: "signed out" },
    never_connected: { dot: ink.textMuted, label: "not connected" },
    // An outage is not a bad session, and asking for a password would not fix
    // one. Say what is true: we could not ask.
    unreachable: { dot: "#B7791F", label: "system not answering" },
    checking: { dot: ink.textMuted, label: "checking…" },
  }[state] ?? { dot: ink.textMuted, label: state };

  return (
    <span style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: dot }} />
        <span style={{ fontSize: 11, color: ink.textSoft }}>{label}</span>
      </span>
      {(state === "signed_out" || state === "never_connected") && (
        <button
          onClick={() => retry.mutate()}
          disabled={retry.isPending}
          style={{
            alignSelf: "flex-start",
            padding: 0,
            border: "none",
            background: "transparent",
            fontSize: 11,
            fontWeight: 700,
            color: ink.accent,
            cursor: "pointer",
          }}
        >
          {retry.isPending ? "Signing in…" : "Sign in again"}
        </button>
      )}
    </span>
  );
}
