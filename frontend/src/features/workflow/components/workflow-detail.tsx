"use client";

/**
 * One mined job, and what it was mined from.
 *
 * The Jobs list can say a job exists. This says why anybody should believe it:
 * every step opens onto the gestures it cites -- what was clicked, what was
 * typed, on which system -- and the calls those gestures carried, request
 * bodies included. A step nobody can open is a step nobody can check, and the
 * skill pages next door have had that for months while a mined workflow had
 * a number ("4 cited") and no way to reach it.
 */

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import {
  listRunsOfWorkflow,
  listWorkflows,
  readEvidence,
  workflowKeys,
  workflowRunKeys,
  type WorkflowModel,
  type WorkflowStepModel,
} from "@/features/workflow/api";
import { became, outcomeLabel, when, whyNotRunnable } from "@/features/workflow/format";
import { RunForm } from "@/features/workflow/components/run-form";
import { Button } from "@/components/ui/button";

/** The recorder's own gesture shape. The route types it loosely, so it is read
 *  defensively rather than off a name the generator does not emit. */
type Gesture = {
  id?: string;
  at?: number;
  url?: string;
  system?: string;
  action?: {
    kind?: string;
    value?: string | null;
    secret?: boolean;
    target?: {
      tag?: string;
      role?: string | null;
      name?: string | null;
      text?: string | null;
      css_path?: string | null;
      xpath?: string | null;
      secret?: boolean;
    } | null;
  } | null;
};

type Call = {
  method?: string;
  url?: string;
  request_body?: { text?: string } | null;
};

const asGesture = (v: unknown): Gesture => (v ?? {}) as Gesture;
const asCalls = (v: unknown): Call[] => (Array.isArray(v) ? (v as Call[]) : []);

const clock = (at?: number) =>
  at === undefined ? "" : new Date(at * 1000).toISOString().slice(11, 19);

const hostOf = (url?: string) => {
  try {
    return url ? new URL(url).host : "";
  } catch {
    return url ?? "";
  }
};

function say(error: unknown): string {
  return error instanceof ApiError ? error.message : String(error);
}

export function WorkflowDetail({ workflowId }: { workflowId: string }) {
  // There is no `GET /v1/workflows/{id}` -- the list route is the only reader,
  // so the detail page shares its cache rather than opening a door for one row.
  const workflows = useQuery({ queryKey: workflowKeys.all, queryFn: listWorkflows });
  const evidence = useQuery({
    queryKey: workflowKeys.evidence(workflowId),
    queryFn: () => readEvidence(workflowId),
  });

  if (workflows.isLoading) return <Skeleton className="h-96 w-full" />;
  if (workflows.error) return <p className="text-destructive">{say(workflows.error)}</p>;

  const job = (workflows.data ?? []).find((w: WorkflowModel) => w.id === workflowId);
  if (!job) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">No such job</h1>
        <p className="text-muted-foreground text-sm">
          Nothing here has this id. A mining pass can retire a job it no longer proposes.{" "}
          <Link href="/knowledge" className="text-brand underline">
            Back to What we know
          </Link>
          .
        </p>
      </div>
    );
  }

  const gestures = (evidence.data?.gestures ?? {}) as Record<string, unknown>;
  const calls = (evidence.data?.requests ?? {}) as Record<string, unknown>;
  const shots = (evidence.data?.shots ?? {}) as Record<string, { url?: string } | undefined>;
  const recordings = evidence.data?.recordings ?? [];
  const missing = evidence.data?.missing ?? [];

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        {/* The list this came from is What we know now, and nothing else on
            this page leads back to it. */}
        <nav aria-label="Breadcrumb" className="text-muted-foreground text-xs">
          <Link
            href="/knowledge"
            className="hover:text-foreground underline-offset-4 hover:underline"
          >
            What we know
          </Link>
          <span aria-hidden> / </span>
          <span>Jobs</span>
        </nav>
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-semibold">{job.title}</h1>
          <span className="text-muted-foreground font-mono text-xs">{job.pass_id}</span>
        </div>
        <p className="text-muted-foreground max-w-3xl text-sm">{job.narrative}</p>
        <div className="flex flex-wrap gap-2">
          {job.systems.map((s: string) => (
            <Badge key={s} variant="outline" className="font-mono text-xs">
              {hostOf(s) || s}
            </Badge>
          ))}
        </div>
        <p className="text-muted-foreground text-xs">{became(job.runs)}</p>
      </header>

      {/* Loudest thing on the page when it is not empty. A cited gesture that
          has aged out of the pool is a step nobody can check again, and the
          job goes on looking exactly as trustworthy as it did yesterday. */}
      {missing.length > 0 && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive text-base">
              {missing.length} cited {missing.length === 1 ? "gesture has" : "gestures have"} gone
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">
              These steps cite evidence that is no longer in the pool, so what they claim can no
              longer be checked against what was recorded.
            </p>
            <pre className="text-muted-foreground mt-2 font-mono text-xs whitespace-pre-wrap">
              {missing.join("\n")}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* The compile check. A job that cannot run is never offered to a request,
          and this is where the operator sees why. */}
      {!job.runnable && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive text-base">This job cannot run yet</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {whyNotRunnable(job.reasons).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Runs, but a reader should know: values fixed at recording, or every
          lane failing lately (tried again after a cool-down). */}
      {job.warnings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Runs, with a warning</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm">
              {whyNotRunnable(job.warnings).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <RunIt job={job} />

      <Parameters job={job} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Steps</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {job.steps.map((step: WorkflowStepModel) => (
            <Step
              key={step.order}
              step={step}
              gestures={gestures}
              calls={calls}
              shots={shots}
              loading={evidence.isLoading}
            />
          ))}
        </CardContent>
      </Card>

      <Runs workflowId={job.id} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {evidence.isLoading && <Skeleton className="h-16 w-full" />}
          {evidence.error && <p className="text-destructive">{say(evidence.error)}</p>}
          {evidence.data && (
            <>
              <p className="text-muted-foreground">
                {Object.keys(gestures).length} gestures · {Object.keys(calls).length} carrying calls
                · {Object.keys(shots).length} photographed · {recordings.length}{" "}
                {recordings.length === 1 ? "recording" : "recordings"}
              </p>
              {recordings.length > 0 && (
                <pre className="text-muted-foreground font-mono text-xs whitespace-pre-wrap">
                  {recordings.join("\n")}
                </pre>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** Run it from here, the same form the list opens inline. */
function RunIt({ job }: { job: WorkflowModel }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle className="text-base">Run this job</CardTitle>
        <Button
          type="button"
          size="sm"
          variant={open ? "secondary" : "default"}
          onClick={() => setOpen(!open)}
        >
          {open ? "Cancel" : "Run"}
        </Button>
      </CardHeader>
      {open && (
        <CardContent>
          <RunForm workflow={job} />
        </CardContent>
      )}
    </Card>
  );
}

/**
 * Every run of this job, newest first.
 *
 * On the job's own page because there is no Runs page any more, and a run is
 * only ever asked about in terms of what it was a run of.
 */
function Runs({ workflowId }: { workflowId: string }) {
  const runs = useQuery({
    queryKey: workflowRunKeys.of(workflowId),
    queryFn: () => listRunsOfWorkflow(workflowId),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Runs</CardTitle>
      </CardHeader>
      <CardContent>
        {runs.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : runs.error ? (
          <p className="text-destructive text-sm">{say(runs.error)}</p>
        ) : runs.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">Never run.</p>
        ) : (
          // Newest first is how the server ordered them; sorting here would be
          // this page inventing an order the row numbers do not agree with.
          <ul className="divide-y text-sm">
            {runs.data.map((run) => (
              <li key={run.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-2">
                <span className="text-muted-foreground font-mono text-xs tabular-nums">
                  {when(run.started_at)}
                </span>
                <span>{outcomeLabel(run)}</span>
                <span className="text-muted-foreground text-xs">by {run.started_by}</span>
                <Link
                  href={`/jobs/runs/${run.id}`}
                  className="text-brand ml-auto text-xs underline"
                >
                  Open
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * What the miner decided varies rather than stays fixed.
 *
 * The skill pages call this "doings that disagree"; here the disagreement is
 * already resolved into `seen_values`, and showing them is the only way to
 * tell a parameter that generalised from two demonstrations apart from one
 * that saw the same string twice and guessed.
 */
function Parameters({ job }: { job: WorkflowModel }) {
  const parameters = (job.parameters ?? []) as { name?: string; seen_values?: string[] }[];
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Parameters</CardTitle>
      </CardHeader>
      <CardContent>
        {parameters.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            None learned. Every value this job used was the same each time it was demonstrated, so
            nothing here is a field somebody fills in.
          </p>
        ) : (
          <div className="space-y-3">
            {parameters.map((p) => (
              <div key={p.name} className="space-y-1">
                <p className="font-mono text-sm">{p.name}</p>
                <div className="flex flex-wrap gap-1.5">
                  {(p.seen_values ?? []).map((v, i) => (
                    <Badge key={`${v}-${i}`} variant="secondary" className="font-mono text-xs">
                      {v}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Step({
  step,
  gestures,
  calls,
  shots,
  loading,
}: {
  step: WorkflowStepModel;
  gestures: Record<string, unknown>;
  calls: Record<string, unknown>;
  shots: Record<string, { url?: string } | undefined>;
  loading: boolean;
}) {
  const [open, setOpen] = useState(false);
  const cites = step.cites ?? [];
  // A cite the evidence route did not return is one that has aged out. Counted
  // here as well as in `missing`, because a reader looking at ONE step should
  // not have to cross-reference a list at the top of the page.
  const gone = cites.filter((id: string) => !(id in gestures)).length;

  return (
    <div className="border-border/60 border-t py-2 first:border-t-0">
      <div className="flex items-start gap-3">
        <span className="text-muted-foreground w-6 shrink-0 text-right font-mono text-xs">
          {step.order}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm">{step.says}</p>
          <p className="text-muted-foreground font-mono text-xs">
            {step.system ? hostOf(step.system) : "system unknown"} · {cites.length} cited
            {gone > 0 && <span className="text-destructive"> · {gone} gone</span>}
          </p>
        </div>
        {cites.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="text-brand shrink-0 text-xs underline"
            aria-expanded={open}
          >
            {open ? "hide" : "show"} evidence
          </button>
        )}
      </div>

      {open && (
        <div className="mt-2 ml-9 space-y-2">
          {loading && <Skeleton className="h-12 w-full" />}
          {cites.map((id: string) => (
            <Cited key={id} id={id} gesture={gestures[id]} calls={calls[id]} shot={shots[id]} />
          ))}
        </div>
      )}
    </div>
  );
}

function Cited({
  id,
  gesture,
  calls,
  shot,
}: {
  id: string;
  gesture: unknown;
  calls: unknown;
  shot?: { url?: string };
}) {
  if (gesture === undefined) {
    return (
      <p className="text-destructive font-mono text-xs">
        {id} — no longer in the pool, so this step cannot be checked against it
      </p>
    );
  }
  const g = asGesture(gesture);
  const target = g.action?.target ?? null;
  const kind = g.action?.kind ?? "?";
  const value = g.action?.value;
  // `secret` is the recorder saying it redacted this. Rendering a redacted
  // field as an empty one would read as "nothing was typed here".
  const redacted = Boolean(g.action?.secret || target?.secret);
  const label = (target?.name ?? target?.text ?? "").replace(/\s+/g, " ").trim();

  // Writes only, and only to the host the gesture happened on.
  //
  // Without the host test this drowns. One click in Gmail carried nineteen
  // POSTs to play.google.com/log, waa-pa.clients6.google.com and
  // appsgenaiserver-pa -- telemetry beacons with base64 bodies, none of them
  // anything an operator did, and together taller than the other six steps
  // combined. The write a step performed goes to the system the step is on;
  // a beacon to somebody else's analytics host never is.
  const here = hostOf(g.url);
  const written = asCalls(calls).filter(
    (c) => (c.method ?? "GET").toUpperCase() !== "GET" && hostOf(c.url) === here,
  );
  // Even same-host, a page can chatter. Three is enough to see what happened;
  // the count keeps the rest from being invisible rather than merely unshown.
  const SHOWN = 3;
  const shown = written.slice(0, SHOWN);
  const rest = written.length - shown.length;

  return (
    <div className="bg-muted/40 rounded-md p-2">
      <p className="font-mono text-xs">
        <span className="text-muted-foreground">{clock(g.at)}</span>{" "}
        <span className="text-foreground">{kind}</span>
        {value !== null && value !== undefined && value !== "" && (
          <span className="text-good"> ={JSON.stringify(value)}</span>
        )}
        {redacted && <span className="text-warn"> · redacted</span>}{" "}
        <span className="text-muted-foreground">{hostOf(g.url)}</span>
      </p>
      {label && <p className="mt-0.5 truncate text-xs">{label}</p>}
      {/* The screen as it was at that instant. The prose above says what the
          model read; this is what it was reading, and it is the only thing on
          the page a person can check without trusting anything the model
          wrote. Lazy, because a step can cite a dozen of them. */}
      {shot?.url && (
        <a href={shot.url} target="_blank" rel="noreferrer" className="mt-1.5 block">
          {/* eslint-disable-next-line @next/next/no-img-element -- a presigned
              URL on a per-request host; next/image would need it in remotePatterns
              and would proxy bytes the browser can already fetch itself. */}
          <img
            src={shot.url}
            alt={`The screen when this gesture happened${label ? `: ${label}` : ""}`}
            loading="lazy"
            className="border-border max-h-56 w-auto rounded border object-contain"
          />
        </a>
      )}
      {shown.map((c, i) => (
        <div key={i} className="mt-1">
          <p className="text-warn font-mono text-xs break-all">
            {c.method} {c.url}
          </p>
          {c.request_body?.text && (
            <pre className="text-muted-foreground mt-0.5 max-h-40 overflow-auto font-mono text-xs whitespace-pre-wrap">
              {c.request_body.text}
            </pre>
          )}
        </div>
      ))}
      {rest > 0 && (
        <p className="text-muted-foreground mt-1 font-mono text-xs">
          and {rest} more {rest === 1 ? "write" : "writes"} to {here}
        </p>
      )}
    </div>
  );
}
