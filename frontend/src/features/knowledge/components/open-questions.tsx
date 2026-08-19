"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  answerQuestion,
  knowledgeKeys,
  listOpenQuestions,
  type OpenQuestion,
} from "@/features/knowledge/api";
import { ApiError } from "@/lib/api/client";

/**
 * The things the system knows it does not know, where somebody can settle them.
 *
 * Induction writes these down instead of guessing — both demonstrations of
 * "create a supplier" used one address, and no amount of evidence in two
 * recordings says whether that is policy or preference. Until now the questions
 * were written and never shown, which is the same as not asking: the guess is
 * just made silently by whichever answer the code happened to prefer.
 *
 * An answer is permanent and shared. It supersedes the question for the whole
 * tenant, and the next induction of that task reads it instead of asking again.
 */
export function OpenQuestions({
  compact = false,
  about,
  title,
}: {
  compact?: boolean;
  /**
   * Show only the questions raised about this entity — `client`, `supplier`.
   *
   * A rail of every open question in the tenant is a rail nobody reads: the
   * question about transport-mode fields sat next to a conversation about
   * clients for a week. Asked beside the skill that raised it, while the
   * operator is looking at that skill, it is one click and it is gone.
   */
  about?: string;
  title?: string;
}) {
  const client = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const questions = useQuery({
    queryKey: knowledgeKeys.questions,
    queryFn: listOpenQuestions,
  });

  const answer = useMutation({
    mutationFn: answerQuestion,
    onSuccess: () => {
      // Both: the question disappears, and what is known has grown by one.
      void client.invalidateQueries({ queryKey: knowledgeKeys.questions });
      void client.invalidateQueries({ queryKey: knowledgeKeys.summary });
      toast.success("Answered", {
        description: "Every skill taught after this reads your answer instead of asking.",
      });
    },
    onError: (error) =>
      toast.error("Could not record that", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  // The key is `system/entity/...`, which is what makes a question findable
  // from a skill: both are addressed by what they are about.
  const open = (questions.data ?? []).filter(
    (question) => !about || question.key.split("/")[1] === about,
  );
  if (open.length === 0) return null;

  // One at a time, unless somebody asks for the rest. Three of these stacked
  // above the composer pushed the conversation off the screen, and a question
  // nobody can see past is not being asked -- it is in the way.
  const showing = compact && !expanded ? open.slice(0, 1) : open;
  const rest = open.length - showing.length;

  return (
    <section style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <header style={{ fontSize: 11, letterSpacing: 0.6, opacity: 0.65 }}>
        {title ??
          (compact ? `NEEDS AN ANSWER (${open.length})` : `Needs an answer (${open.length})`)}
      </header>
      {showing.map((question) => (
        <Question
          key={question.key}
          question={question}
          compact={compact}
          busy={answer.isPending}
          onAnswer={(chosen) =>
            answer.mutate({ system: question.system, key: question.key, chosen })
          }
        />
      ))}
      {rest > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          style={{
            alignSelf: "flex-start",
            padding: "4px 0",
            fontSize: 11.5,
            fontWeight: 700,
            background: "none",
            border: "none",
            opacity: 0.7,
            cursor: "pointer",
          }}
        >
          {rest} more to settle
        </button>
      )}
    </section>
  );
}

function Question({
  question,
  compact,
  busy,
  onAnswer,
}: {
  question: OpenQuestion;
  compact: boolean;
  busy: boolean;
  onAnswer: (chosen: string) => void;
}) {
  return (
    <article
      style={{
        border: "1px solid rgba(127,127,127,0.28)",
        borderRadius: 8,
        padding: compact ? "9px 10px" : "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <p style={{ fontSize: compact ? 12 : 13.5, lineHeight: 1.45, margin: 0 }}>
        {question.question}
      </p>
      {/* Why it is being asked. An operator cannot answer a question about
          evidence they cannot see. */}
      <ul style={{ margin: 0, paddingLeft: 14, fontSize: 11, opacity: 0.7 }}>
        {question.because.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {question.options.map((option) => (
          <button
            key={option}
            disabled={busy}
            onClick={() => onAnswer(option)}
            style={{
              padding: "5px 10px",
              fontSize: 11.5,
              borderRadius: 6,
              border: "1px solid rgba(127,127,127,0.35)",
              background: "transparent",
              cursor: busy ? "wait" : "pointer",
            }}
          >
            {option}
          </button>
        ))}
      </div>
    </article>
  );
}
