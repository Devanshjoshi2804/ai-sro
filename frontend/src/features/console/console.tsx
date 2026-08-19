"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Watching } from "@/features/console/watching";
import { PursuitCard } from "@/features/console/pursuit-card";
import {
  recordingKeys,
  startRecording,
  type ObjectiveKey,
  type StartRecordingRequest,
} from "@/features/recording/api";
import { induceSkill, listSkills, skillKeys } from "@/features/skill/api";
import { api, ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";
import { BatchCard } from "@/features/console/batch-card";
import { SkillCard } from "@/features/console/skill-card";
import { OpenQuestions } from "@/features/knowledge/components/open-questions";
import { TeachPanel } from "@/features/console/teach-panel";
import { useThread } from "@/features/console/thread-store";
import { TopBar, BarLink } from "@/features/console/top-bar";
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
  listThreads,
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

export function Console({ threadId: fromUrl }: { threadId?: string } = {}) {
  const queryClient = useQueryClient();
  const thread = useThread();

  const [tab, setTab] = useState<"chat" | "teach">("chat");
  const [plusOpen, setPlusOpen] = useState(false);
  const [teachingAt, setTeachingAt] = useState<Teaching | null>(null);
  const [active, setActive] = useState<{ recordingId: string; run: number } | null>(null);
  // What the operator is being asked after a run seals. A demonstration ends
  // with a decision -- carry on, or do that one again -- because the operator
  // is the only one who knows whether what they just did was the task.
  const [pending, setPending] = useState<"after-one" | "after-two" | null>(null);
  const [connecting, setConnecting] = useState<true | { base_url: string } | null>(null);
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
  // Asked of the systems themselves, and asked again while the console is open:
  // a session dies on the system's schedule, not on ours, and the whole point is
  // to say so before a demonstration walks into a login page.
  const health = useQuery({
    queryKey: connectionKeys.health,
    queryFn: checkSessions,
    refetchInterval: 60_000,
    enabled: (connections.data ?? []).length > 0,
  });
  // Every conversation this tenant has had, so one can be returned to. They
  // were always stored; only the way back was missing.
  const threads = useQuery({ queryKey: threadKeys.all, queryFn: listThreads });

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
    mutationFn: ([first, second]: [string, string | null]) => induceSkill(first, second),
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

    // Run 2 is where the pair completes, and induction is offered rather than
    // fired: run 1 ends with a choice, so run 2 ends with one too -- the
    // operator who knows they fumbled the second demonstration should not have
    // to watch it be induced before they can say so.
    setPending(active.run === 1 ? "after-one" : "after-two");
  };

  const redo = (run: number) => {
    if (!teachingAt) return;
    thread.forgetRun(run);
    setPending(null);
    thread.add({ kind: "system", text: `Run ${run} discarded. Doing it again.` });
    start.mutate({ form: teachingAt, run });
  };

  const carryOn = () => {
    if (!teachingAt) return;
    setPending(null);
    start.mutate({ form: teachingAt, run: 2 });
  };

  const induceThePair = () => {
    const pair = thread.sealedRecordings.slice(0, 2);
    if (pair.length < 2) return;
    setPending(null);
    induce.mutate([pair[0], pair[1]]);
  };

  /** One demonstration is the whole task, exactly as it was done. */
  const induceFromRunOne = () => {
    const [first] = thread.sealedRecordings;
    if (!first) return;
    setPending(null);
    induce.mutate([first, null]);
  };

  // Nothing taught, nothing proposed, nothing running: the only state where an
  // invitation to teach is the most useful thing on screen.
  const lastDecision = (conversation.data?.messages ?? [])
    .filter((message) => message.decision)
    .at(-1)?.decision as
    | { matched_skill_id?: string | null; choices?: string[] }
    | undefined;
  // Not while there is a choice on the table. Asking "which did you mean?" and
  // printing a teach form underneath it tells the operator both that the task
  // exists twice and that it does not exist at all.
  const offeredAChoice = (lastDecision?.choices ?? []).length > 0;
  const showTeach =
    (conversation.data?.messages ?? []).length === 0 ||
    (lastDecision?.matched_skill_id == null && !offeredAChoice);

  // What this conversation is about, taken from the last thing that matched.
  // `why` is the matcher's own account of the hit -- "entity: client" -- which
  // is the same word the question's key is addressed by.
  const subjectOfThread = ((conversation.data?.messages ?? [])
    .map((message) => (message.decision as { why?: string[] } | undefined)?.why ?? [])
    .flat()
    .filter((reason) => reason.startsWith("entity: "))
    .at(-1) ?? "")
    .replace("entity: ", "");

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
        {/* The console had no way out of itself: every other surface carries
            these, and an operator who wanted to look at a skill had to know the
            URL. */}
        <BarLink href="/recordings">Recordings</BarLink>
        <BarLink href="/skills">Skills</BarLink>
        <BarLink href="/runs">Runs</BarLink>
        <BarLink href="/knowledge">What we know</BarLink>
      </TopBar>

      {connecting ? (
        <div style={{ flex: 1, minHeight: 0 }}>
          <ConnectPanel
            onDone={() => setConnecting(null)}
            reconnect={connecting === true ? undefined : connecting}
          />
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
            {/* What this rail is for: the things that are true *now*, in this
                conversation. A browser being driven, the systems it is driving,
                and the conversations themselves. Everything with a page of its
                own -- skills, recordings, runs -- is a link in the bar above,
                and the questions moved to where they are actually answerable:
                beside the skill that raised them. */}
            <Watching />

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
                    onReconnect={() => setConnecting({ base_url: connection.base_url })}
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
              {(threads.data ?? []).slice(0, 8).map((thread) => (
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
                    // The one you are in, marked. Without the URL there was no
                    // "the one you are in".
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
                          {/* What comes next is the choice underneath, not a
                              sentence here: this line is the receipt. */}
                          Run {entry.run} sealed with {entry.frames} step
                          {entry.frames === 1 ? "" : "s"}.
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

                {/* A run ends with a decision, not with a button that only
                    goes forward. The operator is the only one who knows whether
                    what they just demonstrated was the task -- a wrong turn, a
                    validation error, the wrong client picked -- and before this
                    the only way to say so was to teach the whole thing again
                    from the beginning and hope the right two runs paired. */}
                {pending && teachingAt && !teaching && (
                  <div style={{ display: "flex", gap: 12 }}>
                    <Avatar />
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      <div style={{ fontSize: 15, lineHeight: 1.6 }}>
                        {pending === "after-one"
                          ? "Run 1 captured. Do it once more with different values — the two runs are diffed, and what changes between them becomes the parameters. Or take run 1 on its own: it will replay exactly what you just did, with no parameters to fill in."
                          : "Both runs captured. Induce the skill, or do run 2 again if that one went wrong."}
                      </div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <Choice
                          primary
                          pending={start.isPending || induce.isPending}
                          onClick={pending === "after-one" ? carryOn : induceThePair}
                        >
                          {pending === "after-one" ? "Continue to run 2" : "Induce the skill"}
                        </Choice>
                        {/* A second demonstration is not always worth what it
                            costs -- a task done once a quarter, a screen already
                            walked through twice. One run makes a skill that
                            replays exactly what was done, and the card says so
                            rather than implying parameters it does not have. */}
                        {pending === "after-one" && (
                          <Choice
                            pending={start.isPending || induce.isPending}
                            onClick={induceFromRunOne}
                          >
                            Use run 1 on its own
                          </Choice>
                        )}
                        <Choice
                          pending={start.isPending || induce.isPending}
                          onClick={() => redo(pending === "after-one" ? 1 : 2)}
                        >
                          {pending === "after-one" ? "Redo run 1" : "Redo run 2"}
                        </Choice>
                      </div>
                    </div>
                  </div>
                )}

                {/* Opening a session can fail on its own -- a browser already in
                    use, most often -- and that is not a decision, it is a
                    retry. */}
                {teachingAt && !teaching && !pending && runsSoFar === 0 && (
                  <div style={{ display: "flex", gap: 12 }}>
                    <Avatar />
                    <Choice primary pending={start.isPending} onClick={() => redo(1)}>
                      Try opening a session again
                    </Choice>
                  </div>
                )}

                {/* Only when there is nothing to answer with. Offering to be
                    taught underneath every reply — including replies that found
                    the right skill and ran it — reads as though nothing worked.
                    Teaching is always available from the + button. */}
                {teachingAt === null && showTeach && (
                  <TeachForm
                    onStart={beginTeaching}
                    pending={start.isPending}
                    systems={(connections.data ?? []).map((connection) => ({
                      name: connection.name,
                      base_url: connection.base_url,
                    }))}
                  />
                )}
              </div>
            </div>

            <div style={{ flex: "0 0 auto", padding: "0 28px 24px" }}>
              <div style={{ maxWidth: 772, margin: "0 auto", position: "relative" }}>
                {/* One question, about what this conversation is on, directly
                    above where the operator is already looking. Rendered per
                    skill card it appeared under every card in the transcript --
                    the same two questions four times down one thread, which is
                    worse than the rail it replaced. */}
                {subjectOfThread && (
                  <div style={{ paddingBottom: 12 }}>
                    <OpenQuestions
                      compact
                      about={subjectOfThread}
                      title="I COULD NOT DECIDE THIS FROM THE DEMONSTRATIONS"
                    />
                  </div>
                )}
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
  systems,
}: {
  onStart: (startUrl: string) => void;
  pending: boolean;
  /** The systems already connected, with the address each was connected at. */
  systems: { name: string; base_url: string }[];
}) {
  const [url, setUrl] = useState("");
  const [typing, setTyping] = useState(false);

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
          {systems.length > 0
            ? "The system you connected already said where it lives. Start there and navigate to the screen yourself — capture begins with the browser."
            : "Paste the screen you would open to do it, or leave it blank and navigate there yourself — capture starts with the browser either way."}{" "}
          Nothing else is asked: what the task is gets read off what it does — the call it ends on
          names the entity and the action.
        </div>

        {/* A connected system already carries its address; asking for it again
            is asking the operator to fetch something the system has. The same
            button in Connect a system opens that address, and this is the same
            act with a recorder attached. */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {systems.map((system) => (
            <button
              key={system.base_url}
              onClick={() => onStart(system.base_url)}
              disabled={pending}
              style={{
                padding: "10px 16px",
                borderRadius: 8,
                border: "none",
                background: pending ? "#E7E7E4" : ink.accent,
                color: pending ? ink.textMuted : "#fff",
                fontSize: 13,
                fontWeight: 700,
                cursor: pending ? "not-allowed" : "pointer",
              }}
            >
              {pending ? "Opening a browser…" : `Teach on ${system.name}`}
            </button>
          ))}

          {(systems.length === 0 || typing) && (
            <button
              onClick={() => onStart(url.trim())}
              disabled={pending}
              style={{
                padding: "10px 16px",
                borderRadius: 8,
                border: systems.length === 0 ? "none" : `1px solid ${ink.line}`,
                background: systems.length === 0 ? (pending ? "#E7E7E4" : ink.accent) : "transparent",
                color: systems.length === 0 ? (pending ? ink.textMuted : "#fff") : ink.textSoft,
                fontSize: 13,
                fontWeight: 700,
                cursor: pending ? "not-allowed" : "pointer",
              }}
            >
              {pending ? "Opening a browser…" : "Open a session and start run 1"}
            </button>
          )}

          {systems.length > 0 && !typing && (
            <button
              onClick={() => setTyping(true)}
              style={{
                padding: "10px 14px",
                borderRadius: 8,
                border: `1px solid ${ink.line}`,
                background: "transparent",
                color: ink.textSoft,
                fontSize: 12.5,
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Somewhere else
            </button>
          )}
        </div>

        {(systems.length === 0 || typing) && (
          <Field
            label="Start URL — optional"
            placeholder="https://wms.acme-dc.internal/inventory"
            value={url}
            onChange={setUrl}
          />
        )}
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

/** One of the two answers a finished run asks for. */
function Choice({
  children,
  onClick,
  primary = false,
  pending = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  primary?: boolean;
  pending?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={pending}
      style={{
        padding: "10px 16px",
        borderRadius: 8,
        background: primary ? ink.accent : "transparent",
        color: primary ? "#fff" : ink.textSoft,
        border: primary ? "none" : `1px solid ${ink.line}`,
        fontSize: 13,
        fontWeight: 700,
        cursor: pending ? "default" : "pointer",
        opacity: pending ? 0.6 : 1,
      }}
    >
      {children}
    </button>
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
          <span style={{ fontFamily: mono, fontSize: 11.5, color: ink.textMuted }}>
            {seconds}s
          </span>
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


function ChatTurn({
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
    run_id?: string | null;
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

        {/* Nothing taught for this, but the knowledge base knows the screen.
            Offered rather than taken: driving somebody's warehouse is theirs
            to authorise, and this button is that authorisation. */}
        {!decision.matched_skill_id && threadId && system && askedFor && (
          <PursuitCard threadId={threadId} intent={askedFor} system={system} />
        )}

        {decision.note && <div style={{ fontSize: 12, color: ink.textSoft }}>{decision.note}</div>}

        {/* A question with the answers next to it. Printing "which did you
            mean: A or B?" and then leaving the operator to retype one of them
            is a dead end wearing the face of a conversation. */}
        {choices.length > 0 && onAsk && <Choices ids={choices} onPick={onAsk} />}

        {/* A request this system composed rather than replayed: nobody taught
            "supplier TESTSUPPLIERSRO", the field dictionary said what that
            value is called and the taught read proved the filter. */}
        {decision.derived && (
          <Derived found={decision.derived} suggestions={decision.suggestions ?? []} onAsk={onAsk} />
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
    // No stored credentials is the common case, not an error worth a toast:
    // it means this system is signed into by hand, so open the window and
    // watch it. What went wrong before was opening one nothing was watching.
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
      {(state === "signed_out" || state === "never_connected") && (
        <KeepSignedIn connectionId={connection.id} />
      )}
    </span>
  );
}

/**
 * Sign this system in by itself, from now on.
 *
 * The identity provider will not issue this deployment a credential of its
 * own: the WMS client is public and permitted one flow, and the realm accepts
 * only the redirect the application itself registered. So the way to stop an
 * expired session interrupting work is the way a person would do it — open the
 * system's own login page and sign in — done by the system, on its own, at the
 * moment it finds itself signed out.
 *
 * The password is typed into that page and nowhere else. It is encrypted in
 * the vault, returned by no request, written into no recording, and used
 * against no host but this connection's own.
 */
function KeepSignedIn({ connectionId }: { connectionId: string }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ username: "", password: "" });

  const keep = useMutation({
    mutationFn: async () => {
      await api.put(`/v1/connections/${connectionId}/credentials`, {
        username: form.username.trim(),
        password: form.password,
      });
      return api.post(`/v1/connections/${connectionId}/sign-in?target_system=blue_yonder`);
    },
    onSuccess: () => {
      toast.success("It will sign itself in from now on");
      setOpen(false);
      setForm({ username: "", password: "" });
      void queryClient.invalidateQueries({ queryKey: connectionKeys.health });
    },
    onError: (error) =>
      toast.error("Could not sign in", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          alignSelf: "flex-start",
          padding: 0,
          border: "none",
          background: "transparent",
          fontSize: 11,
          color: ink.textMuted,
          cursor: "pointer",
          textDecoration: "underline",
        }}
      >
        Stop asking me
      </button>
    );
  }

  const ready = form.username.trim() && form.password;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5, paddingTop: 4 }}>
      {(["username", "password"] as const).map((field) => (
        <input
          key={field}
          type={field === "password" ? "password" : "text"}
          value={form[field]}
          placeholder={field}
          autoComplete={field === "password" ? "new-password" : "username"}
          onChange={(event) => setForm({ ...form, [field]: event.target.value })}
          style={{
            border: `1px solid ${ink.line}`,
            borderRadius: 6,
            padding: "5px 7px",
            fontSize: 11.5,
            fontFamily: mono,
            outline: "none",
          }}
        />
      ))}
      <button
        onClick={() => keep.mutate()}
        disabled={!ready || keep.isPending}
        style={{
          border: "none",
          borderRadius: 6,
          padding: "5px 8px",
          background: ready ? ink.accent : "#E7E7E4",
          color: ready ? "#fff" : ink.textMuted,
          fontSize: 11,
          fontWeight: 700,
          cursor: ready ? "pointer" : "not-allowed",
        }}
      >
        {keep.isPending ? "Signing in…" : "Keep me signed in"}
      </button>
      <span style={{ fontSize: 10, color: ink.textMuted, lineHeight: 1.5 }}>
        Encrypted in the vault, typed into this system&rsquo;s own login page and nowhere else.
      </span>
    </div>
  );
}
