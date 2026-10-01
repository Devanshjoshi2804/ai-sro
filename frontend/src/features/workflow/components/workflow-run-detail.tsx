"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  abortWorkflowRun,
  approveWorkflowRun,
  getWorkflowRun,
  workflowRunKeys,
  type WorkflowRunStepModel,
} from "@/features/workflow/api";
import { PasswordPrompt } from "@/features/workflow/components/password-prompt";
import { money, outcomeLabel, when } from "@/features/workflow/format";

/** A verdict a reader must not have to squint at. */
const VERDICT_COLOUR: Record<string, string> = {
  held: "text-good",
  failed: "text-destructive",
  refused: "text-destructive",
  withheld: "text-warn",
};

/**
 * `withheld` comes off the wire as a bare dict, so nothing here may assume a
 * field is there. `planned` always is; `method`, `url` and `body` exist only
 * when a call was recorded against the step.
 */
function withheldText(w: Record<string, unknown>): string {
  const s = (v: unknown) => (v === null || v === undefined ? "" : String(v));
  return [
    `step ${s(w.step)}`,
    `${s(w.method)} ${s(w.url)}`,
    s(w.body),
    JSON.stringify(w.planned ?? {}, null, 2),
  ].join("\n");
}

export function WorkflowRunDetail({ runId }: { runId: string }) {
  const queryClient = useQueryClient();

  const run = useQuery({
    queryKey: workflowRunKeys.detail(runId),
    queryFn: () => getWorkflowRun(runId),
    // Only while it is running. Every other outcome is terminal, so a poll
    // after one of them asks a question that can never come back different —
    // and it would keep re-rendering a finished run's withheld writes, which
    // are the entire point of having done a dry run at all.
    refetchInterval: (query) => (query.state.data?.outcome === "running" ? 1000 : false),
  });

  const again = () => queryClient.invalidateQueries({ queryKey: workflowRunKeys.detail(runId) });

  const approve = useMutation({
    mutationFn: () => approveWorkflowRun(runId),
    onSuccess: () => {
      toast.success("approved — the run goes on");
      again();
    },
    onError: (error) => toast.error("approve refused", { description: String(error) }),
  });

  const stop = useMutation({
    mutationFn: () => abortWorkflowRun(runId),
    onSuccess: () => {
      toast.success("stopped");
      again();
    },
    onError: (error) => toast.error("stop refused", { description: String(error) }),
  });

  if (run.isLoading) return <Skeleton className="h-96 w-full" />;
  if (run.error) return <p className="text-destructive">{String(run.error)}</p>;
  if (!run.data) return null;

  const it = run.data;
  const running = it.outcome === "running";
  // Parked, not merely running: a run with nothing awaiting has nothing for a
  // person to approve, and offering the press anyway is offering a no-op.
  const parked = running && it.steps.some((s) => s.verdict === "awaiting");

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1">
          {/* A run is read in terms of the job it was a run of, and this page
              was a dead end: the only way back was the browser's. */}
          <nav aria-label="Breadcrumb" className="text-muted-foreground text-xs">
            <Link
              href="/knowledge"
              className="hover:text-foreground underline-offset-4 hover:underline"
            >
              What we know
            </Link>
            <span aria-hidden> / </span>
            <Link
              href={`/jobs/${it.workflow_id}`}
              className="hover:text-foreground underline-offset-4 hover:underline"
            >
              The job
            </Link>
            <span aria-hidden> / </span>
            <span>Run</span>
          </nav>
          <h1 className="text-2xl font-semibold tracking-tight">{outcomeLabel(it)}</h1>
          <p className="text-muted-foreground font-mono text-xs">
            {it.id} · started {when(it.started_at)}
            {it.finished_at ? ` · finished ${when(it.finished_at)}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn("font-mono text-sm", it.unpriced && "text-warn")}>{money(it)}</span>
          {parked && (
            <Button disabled={approve.isPending} onClick={() => approve.mutate()}>
              Approve
            </Button>
          )}
          {running && (
            <Button variant="destructive" disabled={stop.isPending} onClick={() => stop.mutate()}>
              Stop
            </Button>
          )}
        </div>
      </header>

      <PasswordPrompt run={it} onSent={again} />

      <section className="space-y-2">
        {it.steps.map((s: WorkflowRunStepModel) => (
          <div
            key={s.order}
            data-verdict={s.verdict}
            className={cn("rounded-md border px-4 py-3 text-sm", VERDICT_COLOUR[s.verdict])}
          >
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-muted-foreground tabular-nums">#{s.order}</span>
              <span className="flex-1">{s.says}</span>
              <span>
                <strong>{s.verdict}</strong>
                {s.verdict_by ? ` by ${s.verdict_by}` : ""}
                {s.matched_by ? ` · matched ${s.matched_by}` : ""}
                {s.stale ? " · stale" : ""}
              </span>
              <span className={cn("font-mono text-xs", s.unpriced && "text-warn")}>{money(s)}</span>
            </div>
            {s.reason && <p className="text-muted-foreground mt-1 text-xs">{s.reason}</p>}
          </div>
        ))}
      </section>

      {/* No heading when nothing was withheld: an empty "what a live run would
          have sent" reads as a claim that a live run would have sent nothing. */}
      {it.withheld.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">what a live run would have sent</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {it.withheld.map((w, index) => (
              <pre
                key={index}
                className="bg-muted overflow-x-auto rounded-md p-3 font-mono text-xs whitespace-pre-wrap"
              >
                {withheldText(w)}
              </pre>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
