"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataView } from "@/components/data-view";
import {
  abortWorkflowRun,
  approveWorkflowRun,
  listAwaitingRuns,
  listWorkflows,
  workflowKeys,
  workflowRunKeys,
  type WorkflowRunModel,
  type WorkflowRunStepModel,
} from "@/features/workflow/api";

/**
 * `outcome` beside the verdict: a step left awaiting on a run that already
 * failed or was aborted is not waiting on anybody, and a tap on it would
 * record a person letting out a write nothing is holding open. The list route
 * answers `awaiting=true` off the step alone, so the run's own outcome is
 * checked here too.
 */
function isParked(run: WorkflowRunModel): boolean {
  return run.outcome === "running" && run.steps.some((s) => s.verdict === "awaiting");
}

/** The step the backend would approve: the highest-ordered one still waiting. */
function parkedStep(run: WorkflowRunModel): WorkflowRunStepModel | undefined {
  return run.steps.filter((s) => s.verdict === "awaiting").sort((a, b) => b.order - a.order)[0];
}

/** Task 8 mounts this in the bar. Same filter as the screen, so the badge and
 *  the page can never disagree about what is waiting. */
export function useAwaitingCount(): number {
  const runs = useQuery({
    queryKey: workflowRunKeys.awaiting,
    queryFn: listAwaitingRuns,
    refetchInterval: 3000,
  });
  return (runs.data ?? []).filter(isParked).length;
}

export function NeedsAPerson() {
  const runs = useQuery({
    queryKey: workflowRunKeys.awaiting,
    queryFn: listAwaitingRuns,
    refetchInterval: 3000,
  });
  const workflows = useQuery({
    queryKey: workflowKeys.all,
    queryFn: listWorkflows,
    refetchInterval: 3000,
  });

  const parked = (runs.data ?? []).filter(isParked);
  const titleOf = (workflowId: string) =>
    (workflows.data ?? []).find((w) => w.id === workflowId)?.title ?? workflowId;

  return (
    <DataView
      title="Needs a person"
      description="A run has stopped at a write and is holding a live browser open until somebody answers."
      loading={runs.isLoading}
      error={runs.error}
      rows={parked}
      empty={{
        line: "Nothing is waiting on a person.",
        hint: "When a run reaches a write it has not earned the right to send unasked, it stops here.",
      }}
    >
      {(shown) => (
        <div className="space-y-4">
          {shown.map((run) => (
            <Parked key={run.id} run={run} title={titleOf(run.workflow_id)} />
          ))}
        </div>
      )}
    </DataView>
  );
}

function Parked({ run, title }: { run: WorkflowRunModel; title: string }) {
  const queryClient = useQueryClient();
  const step = parkedStep(run);

  const settle = () => {
    void queryClient.invalidateQueries({ queryKey: workflowRunKeys.awaiting });
    void queryClient.invalidateQueries({ queryKey: workflowRunKeys.all });
  };

  const approve = useMutation({ mutationFn: () => approveWorkflowRun(run.id), onSuccess: settle });
  const stop = useMutation({ mutationFn: () => abortWorkflowRun(run.id), onSuccess: settle });
  // On the card, not in a toast: with several parked runs a toast cannot say
  // which one refused.
  const refusal = approve.error ?? stop.error;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-muted-foreground font-mono text-xs">{run.device_id}</p>
      </CardHeader>
      <CardContent className="space-y-3">
        {step && <p className="text-sm">{`step ${step.order} · ${step.says}`}</p>}
        {/* A person cannot approve what they cannot see. */}
        <pre className="bg-muted overflow-x-auto rounded-md p-3 font-mono text-xs whitespace-pre-wrap">
          {JSON.stringify(step?.sent ?? {}, null, 2)}
        </pre>
        <div className="flex flex-wrap items-center gap-2">
          {/* No device id and no device secret: the console holds the tenant's
              credential and has no browser of its own, so the row records no
              browser rather than one nobody proved. */}
          <Button size="sm" disabled={approve.isPending} onClick={() => approve.mutate()}>
            Approve
          </Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={stop.isPending}
            onClick={() => stop.mutate()}
          >
            Stop
          </Button>
          <Link href={`/jobs/runs/${run.id}`} className="text-brand text-sm underline">
            details
          </Link>
        </div>
        {refusal && <p className="text-destructive text-xs">{refusal.message}</p>}
      </CardContent>
    </Card>
  );
}
