"use client";

import { useQuery } from "@tanstack/react-query";
import { getRun, runKeys, type StepOutcomeModel } from "@/features/run/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const DISPOSITION_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  // The expected case, and therefore the quiet one. As the accent it made
  // every ordinary step glow and left a failure to compete with all of them.
  performed: "secondary",
  withheld: "secondary",
  skipped: "outline",
  failed: "destructive",
};

export function RunDetail({ runId }: { runId: string }) {
  const run = useQuery({
    queryKey: runKeys.detail(runId),
    queryFn: () => getRun(runId),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2000 : false),
  });

  if (run.isLoading) return <Skeleton className="h-96 w-full" />;
  if (run.error) return <p className="text-destructive">{String(run.error)}</p>;
  if (!run.data) return null;

  const it = run.data;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Run {new Date(it.started_at).toLocaleString()}
        </h1>
        <p className="text-muted-foreground text-sm">
          {it.skill_id} v{it.skill_version} · {it.stage} · performed over {it.medium}
          {it.authorized_by ? ` · authorised by ${it.authorized_by}` : ""}
        </p>
        {it.failure && <p className="text-destructive text-sm">{it.failure}</p>}
      </header>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Values</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 font-mono text-xs">
          {Object.entries(it.parameters).map(([name, value]) => (
            <div key={name}>
              ${name} = {value}
            </div>
          ))}
          {/* Read out of the system as it went — the honest answer to "what did
              it actually send", which the parameters alone cannot give. */}
          {Object.entries(it.derived).map(([name, value]) => (
            <div key={name} className="text-muted-foreground">
              ${name} = {value} (read back)
            </div>
          ))}
        </CardContent>
      </Card>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Steps</h2>
        {it.steps.map((step) => (
          <StepOutcome key={step.index} step={step} />
        ))}
        {it.steps.length === 0 && (
          <p className="text-muted-foreground text-sm">Nothing was attempted.</p>
        )}
      </section>
    </div>
  );
}

function StepOutcome({ step }: { step: StepOutcomeModel }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-3 text-base">
          <span className="text-muted-foreground tabular-nums">#{step.index}</span>
          <span className="font-normal">{step.intent}</span>
          <Badge variant={DISPOSITION_VARIANT[step.disposition] ?? "outline"}>
            {step.disposition}
          </Badge>
          {/* Which rung did the work. A step that quietly needs the browser
              every time is a skill drifting from the system it was taught on. */}
          {step.escalated_from && (
            <Badge variant="secondary">
              {step.escalated_from} → {step.medium}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {step.method && (
          <p className="font-mono text-xs break-all">
            {step.method} {step.url} {step.status_code ? `→ ${step.status_code}` : ""}
          </p>
        )}
        {/* The body of the write. The line above says where and whether it
            landed; this says what was in it -- withheld, sent, or failed. */}
        {step.request_body && (
          <pre className="bg-muted overflow-x-auto rounded p-2 font-mono text-[11px] whitespace-pre-wrap">
            {step.request_body}
          </pre>
        )}
        {step.matched_by && (
          <p className="text-muted-foreground text-xs">found by {step.matched_by}</p>
        )}
        {step.escalation_reason && (
          <p className="text-muted-foreground text-xs">{step.escalation_reason}</p>
        )}
        {step.assertion_failures.length > 0 && (
          <ul className="text-destructive space-y-1 text-xs">
            {step.assertion_failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        )}
        {step.detail && <p className="text-muted-foreground text-xs">{step.detail}</p>}
        {step.idempotency_key && (
          <p className="text-muted-foreground font-mono text-[11px]">
            idempotency {step.idempotency_key}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
