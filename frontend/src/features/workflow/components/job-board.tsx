"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataView } from "@/components/data-view";
import {
  listRunsOfWorkflow,
  listWorkflows,
  workflowKeys,
  workflowRunKeys,
  type WorkflowModel,
} from "@/features/workflow/api";
import { became, outcomeLabel, when } from "@/features/workflow/format";
import { RunForm } from "@/features/workflow/components/run-form";

/** The jobs mined out of what operators actually did. */
export function JobBoard() {
  const workflows = useQuery({ queryKey: workflowKeys.all, queryFn: listWorkflows });

  return (
    <DataView
      title="Jobs"
      description="The workflows mined out of what operators actually did."
      loading={workflows.isLoading}
      error={workflows.error}
      rows={workflows.data ?? []}
      matches={(w: WorkflowModel, term) =>
        `${w.title} ${w.narrative} ${w.systems.join(" ")}`.toLowerCase().includes(term)
      }
      empty={{
        line: "Nothing has been mined yet.",
        // The rig's copy named `POST /v1/mine`, which has no button anywhere.
        hint: "A mining pass reads a day of captured gestures and proposes the jobs it saw.",
      }}
    >
      {(shown) => (
        <div className="space-y-3">
          {shown.map((w) => (
            <Job key={w.id} workflow={w} />
          ))}
        </div>
      )}
    </DataView>
  );
}

function Job({ workflow: w }: { workflow: WorkflowModel }) {
  const [showing, setShowing] = useState<"run" | "runs" | null>(null);

  return (
    <Card>
      <CardHeader className="flex items-start justify-between gap-3">
        <CardTitle>
          {/* The card is a summary; the evidence behind it lives on its own
              page. Without this link the citations under each step are a
              count with nothing to open. */}
          <Link href={`/jobs/${w.id}`} className="hover:text-brand underline-offset-4 hover:underline">
            {w.title}
          </Link>
        </CardTitle>
        {/* An id, not a price. One mining call proposes every job in a pass,
            so a per-card dollar figure would draw the whole pass's bill once
            per card. */}
        <span className="text-muted-foreground font-mono text-xs">{w.pass_id}</span>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-muted-foreground text-xs">{w.narrative}</p>
        <p className="font-mono text-xs">{w.systems.join("  ")}</p>
        <p className="text-muted-foreground text-xs">{became(w.runs)}</p>

        <ol className="space-y-2">
          {w.steps.map((s) => (
            <li key={s.order} className="flex gap-2">
              <span className="text-muted-foreground w-5 shrink-0 font-mono text-xs tabular-nums">
                {`${s.order}`}
              </span>
              <div>
                <p className="text-sm">{s.says}</p>
                {/* "system unknown" said, not blanked: a step whose system was
                    never established is not a step in no system. And no
                    pluralisation on "cited", as the rig had it. */}
                <p className="text-muted-foreground text-xs">
                  {`${s.system ?? "system unknown"} · ${s.cites.length} cited`}
                </p>
              </div>
            </li>
          ))}
        </ol>

        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setShowing(showing === "run" ? null : "run")}
          >
            run
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setShowing(showing === "runs" ? null : "runs")}
          >
            past runs
          </Button>
        </div>

        {showing === "run" && <RunForm workflow={w} />}
        {showing === "runs" && <PastRuns workflowId={w.id} />}
      </CardContent>
    </Card>
  );
}

function PastRuns({ workflowId }: { workflowId: string }) {
  const runs = useQuery({
    queryKey: workflowRunKeys.of(workflowId),
    queryFn: () => listRunsOfWorkflow(workflowId),
  });

  if (runs.isPending) return <p className="text-muted-foreground text-xs">reading…</p>;
  if (runs.error)
    return <p className="text-destructive text-xs">{(runs.error as Error).message}</p>;
  if (!runs.data.length) return <p className="text-muted-foreground text-xs">no runs yet</p>;

  // Newest first is how the server ordered them; sorting here would be this
  // page inventing an order the row numbers do not agree with.
  return (
    <ul className="space-y-1">
      {runs.data.map((r) => (
        <li key={r.id} className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-mono">{when(r.started_at)}</span>
          <span>{outcomeLabel(r)}</span>
          <span className="text-muted-foreground">{`by ${r.started_by}`}</span>
          <Link href={`/jobs/runs/${r.id}`} className="text-brand underline">
            open
          </Link>
        </li>
      ))}
    </ul>
  );
}
