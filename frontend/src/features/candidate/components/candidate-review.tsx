"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  candidateKeys,
  dismissCandidate,
  listCandidates,
  teachCandidate,
} from "@/features/candidate/api";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
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
      toast.error(`Could not teach: ${detail}`);
    },
  });

  const dismiss = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      dismissCandidate(id, reason),
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

  if (candidates.isLoading) return <Skeleton className="h-64 w-full" />;
  if (candidates.error) return <p className="text-destructive">{String(candidates.error)}</p>;

  const rows = candidates.data ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
        <p className="text-muted-foreground text-sm">
          Tasks seen at least {SEEN_AT_LEAST} times, watched rather than taught. Teach one to
          induce a skill from what was already captured, or dismiss it.
        </p>
      </div>

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
          {rows.map((candidate) => (
            <TableRow key={candidate.id}>
              <TableCell>
                {candidate.skill_id ? (
                  <Link href={`/skills/${candidate.skill_id}`} className="hover:underline">
                    {candidate.title}
                  </Link>
                ) : (
                  candidate.title
                )}
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
                      Teach
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
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-muted-foreground py-12 text-center">
                Nothing offered yet. Give it a few days of watching.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

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
            placeholder="Why isn't this worth teaching?"
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
    </div>
  );
}
