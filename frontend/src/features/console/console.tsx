"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PursuitCard, offersToExplore } from "@/features/console/pursuit-card";
import { listSkills, skillKeys } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";
import { BatchCard } from "@/features/console/batch-card";
import { SkillCard } from "@/features/console/skill-card";
import { RunPassword } from "@/features/workflow/components/password-prompt";
import { OpenQuestions } from "@/features/knowledge/components/open-questions";
import { TopBar, MainLinks } from "@/features/console/top-bar";
import { connectionKeys, listConnections } from "@/features/console/connect-panel";
import {
  getThread,
  listThreads,
  say,
  startThread,
  threadKeys,
  type ChatMessage,
} from "@/features/console/chat-api";

export function Console({ threadId: fromUrl }: { threadId?: string } = {}) {
  const queryClient = useQueryClient();
  const router = useRouter();
  // The URL is the thread. Held in state as well only so a conversation
  // started in this tab can begin before the route has caught up.
  const [started, setStarted] = useState<string | null>(null);
  const threadId = fromUrl ?? started;
  const [draft, setDraft] = useState("");
  // The sentence currently in flight. Held here because the transcript is the
  // server's, and until it answers there is nothing in it: the operator pressed
  // Enter, their words vanished from the box, and the screen sat unchanged
  // until the whole round trip finished -- which reads as "it did not send".
  const [inFlight, setInFlight] = useState<string | null>(null);

  const connections = useQuery({ queryKey: connectionKeys.all, queryFn: listConnections });
  // Every conversation this tenant has had, so one can be returned to. They
  // were always stored; only the way back was missing.
  //
  // Polled, because the extension's panel writes into the same threads. The
  // panel already reads this store every five seconds; the console read it once
  // and never again, so a sentence typed in the panel appeared here only after
  // a reload -- the two surfaces agreed about the data and not about what was
  // on screen. React Query stops polling while this tab is in the background.
  const threads = useQuery({
    queryKey: threadKeys.all,
    queryFn: listThreads,
    refetchInterval: 15_000,
  });

  // The conversation lives server-side: a reload used to lose it, and what was
  // asked and what the system decided are half of the audit trail.
  const conversation = useQuery({
    queryKey: threadKeys.detail(threadId ?? ""),
    queryFn: () => getThread(threadId as string),
    enabled: threadId !== null,
    // The panel's own rate, so a reply said in one surface is on the other
    // within the same few seconds whichever way round it went.
    refetchInterval: 5_000,
  });

  const ask = useMutation({
    mutationFn: async (text: string) => {
      const id = threadId ?? (await startThread()).id;
      if (threadId === null) {
        setStarted(id);
        // Replace rather than push: the empty console the operator typed into
        // is not a place worth going back to.
        router.replace(`/console/${id}`);
      }
      return say(id, text);
    },
    onMutate: (text: string) => {
      setInFlight(text);
      setDraft("");
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(threadKeys.detail(updated.id), updated);
      void queryClient.invalidateQueries({ queryKey: threadKeys.all });
    },
    onError: (error, text) => {
      // Put it back. Losing what somebody typed because the request failed is
      // the one outcome worse than the failure.
      setDraft(text);
      toast.error("Could not send that", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      });
    },
    onSettled: () => setInFlight(null),
  });

  // What this conversation is about, taken from the last thing that matched.
  // `why` is the matcher's own account of the hit -- "entity: client" -- which
  // is the same word the question's key is addressed by.
  const subjectOfThread = (
    (conversation.data?.messages ?? [])
      .map((message) => (message.decision as { why?: string[] } | undefined)?.why ?? [])
      .flat()
      .filter((reason) => reason.startsWith("entity: "))
      .at(-1) ?? ""
  ).replace("entity: ", "");

  const send = () => {
    if (draft.trim() && !ask.isPending) ask.mutate(draft.trim());
  };

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        fontFamily: "var(--font-body), system-ui, sans-serif",
        color: ink.text,
        background: ink.page,
        overflow: "hidden",
      }}
    >
      {/* The same places as the rest of the console (`MainLinks`). Teaching,
          the browser on the server and the pages that went with them --
          Recordings, Skills, Runs -- are gone: the rig learns from what
          operators already do in their own browser. */}
      <TopBar>
        <MainLinks />
      </TopBar>

      <div style={{ flex: 1, display: "flex", minHeight: 0 }}>
        <aside
          // Hidden in the panel by globals.css: 236px of thread list out of
          // 400 leaves no room for the conversation it is a list of.
          data-console="rail"
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
          <Section title="CONVERSATIONS">
            <Link
              href="/console"
              style={{
                padding: "8px 10px",
                borderRadius: 8,
                fontSize: 12.5,
                fontWeight: 600,
                color: ink.accent,
                border: `1px dashed ${ink.line}`,
              }}
            >
              New conversation
            </Link>
            {(threads.data ?? []).slice(0, 12).map((thread) => (
              <Link
                key={thread.id}
                href={`/console/${thread.id}`}
                style={{
                  padding: "8px 10px",
                  borderRadius: 8,
                  fontSize: 12.5,
                  display: "flex",
                  gap: 7,
                  alignItems: "baseline",
                  background: thread.id === threadId ? ink.infoWash : "transparent",
                  color: thread.id === threadId ? ink.text : ink.textSoft,
                  fontWeight: thread.id === threadId ? 600 : 400,
                }}
              >
                <span
                  style={{
                    flex: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {thread.title}
                </span>
                <span style={{ color: ink.textMuted, fontSize: 11 }}>{thread.message_count}</span>
              </Link>
            ))}
          </Section>
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
              data-console="column"
              style={{
                maxWidth: 772,
                margin: "0 auto",
                padding: "0 28px",
                display: "flex",
                flexDirection: "column",
                gap: 20,
              }}
            >
              {(conversation.data?.messages ?? []).length === 0 && !inFlight ? <Empty /> : null}

              {(conversation.data?.messages ?? []).map((message, index, all) => (
                <ChatTurn
                  key={message.id}
                  message={message}
                  onAsk={setDraft}
                  threadId={threadId ?? undefined}
                  system={(connections.data ?? [])[0]?.target_system}
                  askedFor={askedBefore(conversation.data?.messages ?? [], message.id)}
                  latest={index === all.length - 1}
                />
              ))}

              {inFlight && (
                <>
                  <Operator>{inFlight}</Operator>
                  <Thinking />
                </>
              )}
            </div>
          </div>

          <div style={{ flex: "0 0 auto", padding: "0 28px 24px" }}>
            <div data-console="column" style={{ maxWidth: 772, margin: "0 auto" }}>
              {/* One question, about what this conversation is on, directly
                  above where the operator is already looking. */}
              {subjectOfThread && (
                <div style={{ paddingBottom: 12 }}>
                  <OpenQuestions compact about={subjectOfThread} title="NEEDS AN ANSWER" />
                </div>
              )}

              <form
                // Its focus is drawn on the whole box by globals.css
                // (`[data-console="composer"]`). The input's own ring drew a
                // second rounded box inside the first.
                data-console="composer"
                onSubmit={(event) => {
                  event.preventDefault();
                  send();
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  background: ink.panel,
                  border: `1px solid ${ink.line}`,
                  borderRadius: 14,
                  padding: "9px 9px 9px 16px",
                }}
              >
                <input
                  aria-label="Ask for a task"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder="Ask for a task — “create supplier ACME-4471 at SG”"
                  style={{
                    flex: 1,
                    border: "none",
                    fontSize: 14.5,
                    background: "transparent",
                    color: ink.text,
                  }}
                />
                <button
                  type="submit"
                  disabled={!draft.trim() || ask.isPending}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 9,
                    border: "none",
                    fontSize: 13,
                    fontWeight: 700,
                    background: draft.trim() && !ask.isPending ? ink.accent : ink.disabled,
                    color: draft.trim() && !ask.isPending ? "#fff" : ink.textMuted,
                    cursor: draft.trim() && !ask.isPending ? "pointer" : "not-allowed",
                  }}
                >
                  {ask.isPending ? "Asking…" : "Ask"}
                </button>
              </form>
              <div style={{ padding: "9px 4px 0", fontSize: 11, color: ink.textMuted }}>
                Asking finds the job that does it and says what it still needs. Nothing runs until
                you press Run — that press is what the run records as its authorisation.
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

/**
 * The first screen of a conversation.
 *
 * One line, and no suggestions. It offered the tenant's job titles as buttons
 * for a while, and that was worse than nothing: the first one on the deployed
 * console was "Delete a Customer Type", a job that removes records, offered to
 * somebody who had not asked for anything -- and pressing any of them only
 * pasted a title with none of the values a job needs, so the one thing it
 * taught was that the console suggests things it cannot do. What a tenant can
 * do is on What we know, where each job is shown with what it takes.
 */
function Empty() {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      <Avatar />
      <div style={{ fontSize: 15, lineHeight: 1.6 }}>
        Ask for a task in your own words — what to do and the values to use. I will find the job
        that does it and say what it still needs. Nothing runs until you press Run.
      </div>
    </div>
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

function Operator({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        alignSelf: "flex-end",
        maxWidth: "60%",
        // The operator's own words, as a filled bubble. It was a dark bubble
        // with near-white text on a light page; a literal-for-token pass turned
        // the text into the same token as the fill and made it invisible. On a
        // dark ground the equivalent of "filled" is a *raised* surface, not a
        // darker one.
        background: "var(--brand-raised-2)",
        color: ink.text,
        padding: "11px 15px",
        borderRadius: "14px 14px 4px 14px",
        fontSize: 14.5,
      }}
    >
      {children}
    </div>
  );
}

/**
 * That the question was received and is being worked on.
 *
 * Deliberately not a fake progress bar: this cannot see inside the request, so
 * it says the one thing it knows -- that it is still going -- and after a while
 * says how long, which is the number an operator actually wants when they are
 * deciding whether to wait or reload.
 */
function Thinking() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const tick = setInterval(() => setSeconds((elapsed) => elapsed + 1), 1000);
    return () => clearInterval(tick);
  }, []);

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
      <Avatar />
      <span style={{ fontSize: 14, color: ink.textSoft, display: "flex", gap: 8 }}>
        {seconds < 4
          ? "Reading what you asked"
          : seconds < 12
            ? "Matching it against what has been taught"
            : "Still working — the system is slower than usual"}
        <Dots />
        {seconds >= 8 && (
          <span style={{ fontFamily: mono, fontSize: 11.5, color: ink.textMuted }}>{seconds}s</span>
        )}
      </span>
    </div>
  );
}

function Dots() {
  return (
    <span aria-hidden style={{ fontFamily: mono, letterSpacing: 2 }}>
      <span style={{ animation: "sro-blink 1.2s infinite" }}>.</span>
      <span style={{ animation: "sro-blink 1.2s infinite .2s" }}>.</span>
      <span style={{ animation: "sro-blink 1.2s infinite .4s" }}>.</span>
      <style>{`
        @keyframes sro-blink { 0%, 60%, 100% { opacity: .25 } 30% { opacity: 1 } }
        @media (prefers-reduced-motion: reduce) { span { animation: none !important } }
      `}</style>
    </span>
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
/** What the operator asked, for a reply that is about to be acted on. */
function askedBefore(messages: ChatMessage[], id: string): string | undefined {
  const at = messages.findIndex((message) => message.id === id);
  for (let index = at - 1; index >= 0; index -= 1) {
    if (messages[index].speaker === "operator") return messages[index].text;
  }
  return undefined;
}

function Derived({
  found,
  suggestions = [],
  onAsk,
}: {
  suggestions?: string[];
  onAsk?: (text: string) => void;
  found: {
    url: string;
    because: string;
    rows: number;
    total: number | null;
    columns: string[];
    found: Record<string, string>[];
  };
}) {
  const [showing, setShowing] = useState(false);
  const columns = found.columns.slice(0, 6);

  return (
    <div style={{ border: `1px solid ${ink.line}`, borderRadius: 9, overflow: "hidden" }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
          padding: "9px 12px",
          borderBottom: `1px solid ${ink.lineSoft}`,
          background: ink.infoWash,
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 700 }}>{found.total ?? found.rows}</span>
        <span style={{ fontSize: 12, color: ink.textSoft }}>
          found · asked for by this system, not replayed from a demonstration
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 11.5 }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  style={{
                    textAlign: "left",
                    padding: "7px 10px",
                    fontFamily: mono,
                    fontSize: 10,
                    letterSpacing: 0.4,
                    textTransform: "uppercase",
                    color: ink.textMuted,
                    borderBottom: `1px solid ${ink.line}`,
                    whiteSpace: "nowrap",
                  }}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {found.found.slice(0, 8).map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td
                    key={column}
                    style={{
                      padding: "7px 10px",
                      borderBottom: `1px solid ${ink.lineSoft}`,
                      fontFamily: mono,
                      whiteSpace: "nowrap",
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

      {/* What it was built out of. A request this system wrote is only worth
          trusting if an operator can see the evidence behind it. */}
      <button
        onClick={() => setShowing((was) => !was)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "7px 12px",
          border: "none",
          borderTop: `1px solid ${ink.lineSoft}`,
          background: "transparent",
          fontSize: 11,
          color: ink.textMuted,
          cursor: "pointer",
        }}
      >
        {showing ? "▾" : "▸"} How this request was worked out
      </button>
      {showing && (
        <div
          style={{
            padding: "0 12px 10px",
            fontSize: 11,
            fontFamily: mono,
            color: ink.textSoft,
            wordBreak: "break-all",
            display: "grid",
            gap: 6,
          }}
        >
          <span>{found.because}</span>
          <span>GET {found.url}</span>
        </div>
      )}

      {onAsk && suggestions.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 6,
            flexWrap: "wrap",
            padding: "8px 12px",
            borderTop: `1px solid ${ink.lineSoft}`,
          }}
        >
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => onAsk(suggestion)}
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
      )}
    </div>
  );
}

function Choices({ ids, onPick }: { ids: string[]; onPick: (text: string) => void }) {
  const skills = useQuery({ queryKey: skillKeys.all, queryFn: listSkills });
  const named = ids
    .map((id) => (skills.data ?? []).find((skill) => skill.id === id))
    .filter((skill): skill is NonNullable<typeof skill> => Boolean(skill));

  if (named.length === 0) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {named.map((skill) => (
        <button
          key={skill.id}
          onClick={() => onPick(skill.name)}
          style={{
            padding: "6px 11px",
            borderRadius: 999,
            border: `1px solid ${ink.line}`,
            background: ink.panel,
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {skill.name}
        </button>
      ))}
    </div>
  );
}

export function ChatTurn({
  message,
  onAsk,
  threadId,
  system,
  askedFor,
  latest = false,
}: {
  message: ChatMessage;
  onAsk?: (text: string) => void;
  threadId?: string;
  system?: string;
  askedFor?: string;
  latest?: boolean;
}) {
  if (message.speaker === "operator") return <Operator>{message.text}</Operator>;

  const decision = message.decision as {
    matched_skill_id?: string | null;
    matched_skill_name?: string | null;
    workflow_id?: string | null;
    run_id?: string | null;
    kind?: string;
    asks?: string;
    question_id?: string;
    matched_version?: number | null;
    confident?: boolean;
    runnable?: boolean;
    missing_parameters?: string[];
    why?: string[];
    proposal_sources?: string[];
    items?: Record<string, string>[];
    note?: string;
    choices?: string[];
    suggestions?: string[];
    derived?: {
      url: string;
      because: string;
      rows: number;
      total: number | null;
      columns: string[];
      found: Record<string, string>[];
    };
  };
  const items = decision.items ?? [];
  const choices = decision.matched_skill_id ? [] : (decision.choices ?? []);

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

        {/* Only under "nothing has been taught for that" (`pursuable`).
            Offered rather than taken: driving somebody's warehouse is theirs
            to authorise, and this button is that authorisation. */}
        {offersToExplore(message.decision) && threadId && system && askedFor && (
          <PursuitCard threadId={threadId} intent={askedFor} system={system} />
        )}

        {decision.note && <div style={{ fontSize: 12, color: ink.textSoft }}>{decision.note}</div>}

        {/* The run a yes here started on the backend: without this the
            thread says "Running" and the operator has nowhere to watch it. */}
        {decision.workflow_id && decision.run_id && (
          <Link
            href={`/jobs/runs/${decision.run_id}`}
            style={{ color: ink.accentDeep, fontSize: 12 }}
          >
            Watch the run
          </Link>
        )}

        {/* A run parked on its password: answered in its own box, never typed
            into the chat. */}
        {decision.kind === "run_asks" &&
          decision.asks === "password" &&
          decision.run_id &&
          decision.question_id && (
            <RunPassword runId={decision.run_id} questionId={decision.question_id} />
          )}

        {/* A question with the answers next to it. Printing "which did you
            mean: A or B?" and then leaving the operator to retype one of them
            is a dead end wearing the face of a conversation. */}
        {choices.length > 0 && onAsk && <Choices ids={choices} onPick={onAsk} />}

        {/* A request this system composed rather than replayed: nobody taught
            "supplier TESTSUPPLIERSRO", the field dictionary said what that
            value is called and the taught read proved the filter. */}
        {decision.derived && (
          <Derived
            found={decision.derived}
            suggestions={decision.suggestions ?? []}
            onAsk={onAsk}
          />
        )}

        {decision.matched_skill_id && items.length > 0 && (
          <BatchCard
            skillId={decision.matched_skill_id}
            skillName={`v${decision.matched_version ?? 1}`}
            items={items}
            runnable={decision.runnable !== false}
          />
        )}

        {/* The question has been answered. Offering the taught skill
            underneath it — with a Run button for a task nobody asked to run —
            reads as the system pushing work at somebody who is already done. */}
        {decision.matched_skill_id && !decision.derived && (
          <SkillCard
            skillId={decision.matched_skill_id}
            threadId={threadId}
            suggestions={decision.suggestions ?? []}
            folded={!latest}
            parameters={items.length === 1 ? items[0] : {}}
            missing={items.length ? [] : (decision.missing_parameters ?? [])}
            onAsk={onAsk}
            answeredBy={decision.run_id ?? undefined}
          />
        )}

        {decision.derived && decision.matched_skill_name && (
          <span style={{ fontFamily: mono, fontSize: 11, color: ink.textMuted }}>
            built on {decision.matched_skill_name}
          </span>
        )}
      </div>
    </div>
  );
}
