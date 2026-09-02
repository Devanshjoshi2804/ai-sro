"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  answerJoin,
  candidateKeys,
  dismissCandidate,
  listCandidates,
  teachCandidate,
  teachTogether,
  type JoinModel,
  type TaskCandidateModel,
} from "@/features/candidate/api";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataView } from "@/components/data-view";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const SEEN_AT_LEAST = 3;

export function CandidateReview() {
  const queryClient = useQueryClient();
  const candidates = useQuery({
    queryKey: candidateKeys.all(SEEN_AT_LEAST),
    queryFn: () => listCandidates(SEEN_AT_LEAST),
  });
  const [dismissing, setDismissing] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: candidateKeys.all(SEEN_AT_LEAST) });

  const teach = useMutation({
    mutationFn: teachCandidate,
    onSuccess: (taught) => {
      if (taught.needs_demonstration) {
        toast.info(taught.because ?? "One more doing of this is needed before it can be taught.");
      } else {
        toast.success("Taught. It starts at Shadow.");
      }
      void invalidate();
    },
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      toast.error(`Could not learn it: ${detail}`);
    },
  });

  const answer = useMutation({
    mutationFn: ({
      id,
      otherId,
      kind,
      answer,
    }: {
      id: string;
      otherId: string;
      kind: string;
      answer: "same" | "different";
    }) => answerJoin(id, otherId, kind, answer),
    onSuccess: () => void invalidate(),
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      toast.error(`Could not answer: ${detail}`);
    },
  });

  const merge = useMutation({
    mutationFn: ({ id, otherId }: { id: string; otherId: string }) => teachTogether(id, otherId),
    onSuccess: (taught) => {
      if (taught.needs_demonstration) {
        toast.info(taught.because ?? "One more doing of both halves is needed.");
      } else {
        toast.success("Taught as one skill. It starts at Shadow.");
      }
      void invalidate();
    },
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      toast.error(`Could not learn them as one: ${detail}`);
    },
  });

  const dismiss = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => dismissCandidate(id, reason),
    onSuccess: () => {
      toast.success("Dismissed.");
      setDismissing(null);
      setReason("");
      void invalidate();
    },
    onError: (error) => {
      const detail = error instanceof ApiError ? error.problem.detail : String(error);
      toast.error(`Could not dismiss: ${detail}`);
    },
  });

  const rows = candidates.data ?? [];

  return (
    <>
      <DataView
        title="Candidates"
        description={`Tasks somebody keeps doing here, seen at least ${SEEN_AT_LEAST} times. Learn one from what was already watched, or dismiss it \u2014 nobody is asked to demonstrate anything.`}
        loading={candidates.isLoading}
        error={candidates.error}
        rows={rows}
        matches={(candidate: TaskCandidateModel, term) =>
          `${candidate.title} ${candidate.host}`.toLowerCase().includes(term)
        }
        facet={{ name: "status", of: (candidate: TaskCandidateModel) => candidate.status }}
        empty={{
          line: "Nothing has been noticed yet.",
          hint: `A task appears here once the same piece of work has been seen ${SEEN_AT_LEAST} times in somebody's browser.`,
        }}
      >
        {(shown) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Task</TableHead>
                <TableHead>Host</TableHead>
                <TableHead className="text-right">Seen</TableHead>
                <TableHead className="text-right">Each takes</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {shown.map((candidate) => (
                <TableRow key={candidate.id}>
                  <TableCell>
                    {candidate.skill_id ? (
                      <Link href={`/skills/${candidate.skill_id}`} className="hover:underline">
                        {candidate.title}
                      </Link>
                    ) : (
                      candidate.title
                    )}
                    {(candidate.joins ?? []).map((join) => (
                      <Suggestion
                        key={`${join.kind}:${join.other_id}`}
                        candidate={candidate}
                        join={join}
                        onAnswer={(said) =>
                          answer.mutate({
                            id: candidate.id,
                            otherId: join.other_id,
                            kind: join.kind,
                            answer: said,
                          })
                        }
                        onMerge={() => merge.mutate({ id: candidate.id, otherId: join.other_id })}
                        busy={answer.isPending || merge.isPending}
                      />
                    ))}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">{candidate.host}</TableCell>
                  <TableCell className="text-right tabular-nums">{candidate.times_seen}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {Math.round(candidate.median_duration_ms / 1000)}s
                  </TableCell>
                  <TableCell>
                    <Badge variant={candidate.status === "new" ? "default" : "outline"}>
                      {candidate.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {candidate.status === "new" && (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          disabled={teach.isPending}
                          onClick={() => teach.mutate(candidate.id)}
                        >
                          Learn this one
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setDismissing(candidate.id)}
                        >
                          Dismiss
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataView>

      {/* Outside the shell, not inside its render prop: dismissing asks why,
          and that question belongs to the page rather than to whichever rows
          happen to be on screen. */}
      <Dialog
        open={dismissing !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDismissing(null);
            setReason("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dismiss this candidate</DialogTitle>
          </DialogHeader>
          <Textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why isn't this worth learning?"
          />
          <DialogFooter>
            <Button
              disabled={!reason.trim() || dismiss.isPending}
              onClick={() => dismissing && dismiss.mutate({ id: dismissing, reason })}
            >
              Dismiss
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** What a model noticed about this candidate, and the two words a person can
 * answer it with.
 *
 * The answer is the point, and `same` about a workflow is the one answer that
 * has something to act on: an episode breaks on a host change, so "check the
 * WMS, then record it in the ERP" is two candidates and always will be, and
 * only a person can say the two are one job.
 */
function Suggestion({
  candidate,
  join,
  onAnswer,
  onMerge,
  busy,
}: {
  candidate: TaskCandidateModel;
  join: JoinModel;
  onAnswer: (said: "same" | "different") => void;
  onMerge: () => void;
  busy: boolean;
}) {
  const what =
    join.kind === "workflow"
      ? "looks like half of one job with another task"
      : "looks like the same task as another";

  if (join.answered) {
    const said =
      join.answered === "same"
        ? join.kind === "workflow"
          ? "one job with another task"
          : "the same task as another"
        : "a different task";
    return (
      <p className="text-muted-foreground mt-1 text-xs">
        {said} — {join.answered_by} said so
        {join.kind === "workflow" && join.answered === "same" && candidate.status === "new" && (
          <Button
            size="sm"
            variant="link"
            className="h-auto p-0 pl-2 text-xs"
            disabled={busy}
            onClick={onMerge}
          >
            Learn them as one
          </Button>
        )}
      </p>
    );
  }

  return (
    <p className="text-muted-foreground mt-1 text-xs">
      {what} — {join.because}
      <Button
        size="sm"
        variant="link"
        className="h-auto p-0 pl-2 text-xs"
        disabled={busy}
        onClick={() => onAnswer("same")}
      >
        Same task
      </Button>
      <Button
        size="sm"
        variant="link"
        className="h-auto p-0 pl-2 text-xs"
        disabled={busy}
        onClick={() => onAnswer("different")}
      >
        Different
      </Button>
    </p>
  );
}
