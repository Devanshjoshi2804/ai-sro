// A question this operator has not answered yet.
//
// A run that cannot find a value it needs ends, and the backend writes what it
// could not find into that operator's own conversation: "I could not find
// Customer Type Description for Create a Customer Type. What should it be?".
// The thread is where that lives, and the thread is durable.
//
// What was not durable is the one surface that walked somebody to it. The
// panel took them to the conversation when a FINISHED RUN carried the names --
// and a finished run is one slot. Measured on the deployment, 2026-09-17:
//
//     03:57  run 561ba940  stopped  needs=["To recipients"]   ← question
//     03:59  run 540e141a  held                               ← took the slot
//
// Ninety seconds, and the card carrying the question was gone. The question
// itself sat in the thread, unanswered, for the rest of the morning; the same
// thing happened at 03:36 and again at 04:34.
//
// So a waiting question is read off the CONVERSATION, which cannot be swept by
// the next run, and it is read on the beat -- the minute alarm that already
// wakes this worker -- so it is found while the panel is closed too.
//
// Pure: given a thread, say what is waiting. Nothing here fetches or stores.

/** The decision kind the backend writes a question under. One string, two
 * sides: `domain/chat/asking.py` writes it and this reads it. */
export const NEEDS = "needs_values";

/**
 * The question this conversation is waiting on, or `null`.
 *
 * The newest assistant decision, and only that. Every answer produces a new
 * decision carrying whatever is still outstanding, so the last one is the
 * whole state -- and a conversation that moved on to something else has a
 * newer decision that is not a question, which is exactly when nothing is
 * waiting. Reading further back would raise a banner about a job somebody
 * abandoned twenty minutes ago.
 */
export function questionIn(thread) {
  const messages = thread?.messages || [];
  for (const message of [...messages].reverse()) {
    if (message.speaker !== "assistant") continue;
    const decision = message.decision || {};
    const asks = decision.kind === NEEDS || (decision.kind === "job" && decision.confirm);
    if (!asks || !decision.workflow_id) return null;
    return {
      id: message.id,
      // The chat it is asked in: a question from a mail or a run that came up
      // short has one of its own, and "Answer it" opens it.
      threadId: thread.id || null,
      // The run whose coming up short wrote it, where one did.
      run: decision.from_run || null,
      text: message.text || "",
      title: decision.title || "",
      workflowId: decision.workflow_id,
      missing: Array.isArray(decision.missing) ? decision.missing : [],
      at: message.said_at || null,
    };
  }
  return null;
}

/**
 * The newest question waiting in any of these threads, or `null`.
 *
 * The operator's own conversation and each chat a question was asked in: a
 * question from a mail, or from a run that came up short, is asked in a chat
 * of its own, so reading the conversation alone finds none of them.
 */
export function questionAmong(threads, run = null) {
  const waiting = threads
    .map(questionIn)
    .filter((one) => one && (!run || one.run === run));
  waiting.sort((a, b) => String(b.at || "").localeCompare(String(a.at || "")));
  return waiting[0] || null;
}
