"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  getKnowledgeSummary,
  knowledgeKeys,
  searchKnowledge,
  type KnowledgeEntry,
} from "@/features/knowledge/api";
import { OpenQuestions } from "@/features/knowledge/components/open-questions";
import { listTriggers, triggerKeys, type TriggerModel } from "@/features/trigger/api";
import { firesWhen, firesWhenShort } from "@/features/trigger/fires-when";
import { listWorkflows, workflowKeys, type WorkflowModel } from "@/features/workflow/api";
import { became } from "@/features/workflow/format";
import { RunForm } from "@/features/workflow/components/run-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * What this tenant can do, and what it knows about the systems it does it in.
 *
 * Two pages used to answer these separately: Jobs listed every mined workflow
 * fully expanded -- fourteen jobs, every step of every one, 5,400 pixels -- and
 * What we know counted claims beside a list of taught skills from a path that
 * no longer teaches anything. A person looking for "can it create a supplier?"
 * needs both halves at once: the job that does it, and whether what it relies
 * on is known firmly.
 *
 * So the jobs are the page, one line each, with the steps behind the title
 * where the evidence already lives; and what is known sits beside them. One
 * search box asks both.
 */

const EVIDENCE_ORDER = ["round_trip", "reproduced", "observed", "asserted"] as const;

const EVIDENCE: Record<string, { label: string; meaning: string }> = {
  round_trip: {
    label: "Round trip",
    meaning: "created, read back, changed and removed — all recorded",
  },
  reproduced: { label: "Reproduced", meaning: "run again and matched what was stored" },
  observed: { label: "Observed", meaning: "seen once, with the exchange stored" },
  asserted: { label: "Asserted", meaning: "written down with no stored exchange — not evidence" },
};

type Filter = "all" | "scheduled" | "proven" | "never";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "scheduled", label: "Has a trigger" },
  { id: "proven", label: "Has run" },
  { id: "never", label: "Never run" },
];

const hostOf = (url: string) => {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
};

export function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const term = query.trim().toLowerCase();
  const searching = term.length > 2;

  const jobs = useQuery({ queryKey: workflowKeys.all, queryFn: listWorkflows });
  const triggers = useQuery({ queryKey: triggerKeys.all, queryFn: listTriggers });
  const summary = useQuery({ queryKey: knowledgeKeys.summary, queryFn: getKnowledgeSummary });
  const claims = useQuery({
    queryKey: knowledgeKeys.search(term),
    queryFn: () => searchKnowledge(term),
    enabled: searching,
  });

  const triggersOf = (id: string) => (triggers.data ?? []).filter((t) => t.workflow_id === id);

  const shown = (jobs.data ?? [])
    .filter((job) => {
      if (filter === "scheduled") return triggersOf(job.id).length > 0;
      if (filter === "proven") return job.runs.total > 0;
      if (filter === "never") return job.runs.total === 0;
      return true;
    })
    .filter(
      (job) =>
        !term ||
        `${job.title} ${job.narrative} ${job.systems.join(" ")}`.toLowerCase().includes(term),
    )
    // What has actually been done first, then the rest by name. A job that has
    // run is the one somebody is most likely looking for, and alphabetical
    // among the rest makes near-duplicates sit together where they can be seen.
    .sort(
      (a, b) =>
        Number(b.runs.earned) - Number(a.runs.earned) ||
        b.runs.total - a.runs.total ||
        a.title.localeCompare(b.title),
    );

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">What we know</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            The jobs this tenant has been seen doing, and what is known about the systems they run
            in. Everything here is shared across the team.
          </p>
        </div>
        <Input
          aria-label="Search jobs and what is known"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search — “supplier”, “work area”, an endpoint"
          className="lg:w-96"
        />
      </header>

      <OpenQuestions title="Needs an answer" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section aria-labelledby="jobs-heading" className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="jobs-heading" className="flex items-baseline gap-2 text-lg font-medium">
              Jobs
              {jobs.data && (
                <span className="text-muted-foreground text-sm font-normal tabular-nums">
                  {shown.length === jobs.data.length
                    ? jobs.data.length
                    : `${shown.length} of ${jobs.data.length}`}
                </span>
              )}
            </h2>
            <div role="group" aria-label="Show" className="bg-muted flex rounded-md p-0.5">
              {FILTERS.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  aria-pressed={filter === option.id}
                  onClick={() => setFilter(option.id)}
                  className={cn(
                    "focus-visible:ring-ring rounded px-2.5 py-1 text-xs font-medium focus-visible:ring-2 focus-visible:outline-none",
                    filter === option.id
                      ? "bg-background text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {jobs.isLoading ? (
            <Skeleton className="h-72 w-full" />
          ) : jobs.error ? (
            <p className="text-destructive text-sm">The jobs could not be read.</p>
          ) : shown.length === 0 ? (
            <div className="rounded-lg border border-dashed px-6 py-10 text-center">
              <p className="text-sm">
                {(jobs.data ?? []).length === 0
                  ? "No jobs yet."
                  : term
                    ? `No job matches “${query.trim()}”.`
                    : "No job fits that filter."}
              </p>
              {(jobs.data ?? []).length === 0 && (
                <p className="text-muted-foreground mt-1 text-xs">
                  A mining pass reads the day’s captured work and proposes the jobs it saw.
                </p>
              )}
            </div>
          ) : (
            <ul className="overflow-hidden rounded-lg border">
              {shown.map((job) => (
                <JobRow key={job.id} job={job} triggers={triggersOf(job.id)} />
              ))}
            </ul>
          )}
        </section>

        <aside aria-label="What is known" className="space-y-4">
          {searching && <Claims term={query.trim()} claims={claims} />}
          <Known summary={summary} />
        </aside>
      </div>
    </div>
  );
}

function JobRow({ job, triggers }: { job: WorkflowModel; triggers: TriggerModel[] }) {
  const [running, setRunning] = useState(false);
  const hosts = Array.from(new Set(job.systems.map(hostOf)));

  return (
    <li className="bg-card border-b last:border-b-0">
      <div className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-start">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/jobs/${job.id}`}
              className="hover:text-brand focus-visible:ring-ring rounded font-medium underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
            >
              {job.title}
            </Link>
            {job.runs.earned && (
              <Badge variant="secondary" className="text-good font-normal">
                writes unasked
              </Badge>
            )}
            {triggers.map((trigger) => (
              <TriggerChip key={trigger.id} trigger={trigger} />
            ))}
          </div>
          {job.narrative && (
            <p className="text-muted-foreground line-clamp-1 text-sm">{job.narrative}</p>
          )}
          <p className="text-muted-foreground flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            {hosts.map((host) => (
              <span key={host} className="bg-muted rounded px-1.5 py-0.5 font-mono">
                {host}
              </span>
            ))}
            <span className="tabular-nums">
              {job.steps.length} step{job.steps.length === 1 ? "" : "s"}
            </span>
            <span aria-hidden>·</span>
            <span className="tabular-nums">{became(job.runs)}</span>
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            type="button"
            size="sm"
            variant={running ? "secondary" : "outline"}
            aria-expanded={running}
            onClick={() => setRunning((open) => !open)}
          >
            {running ? "Cancel" : "Run"}
          </Button>
          <Link
            href={`/jobs/${job.id}`}
            className="text-muted-foreground hover:text-foreground focus-visible:ring-ring inline-flex h-8 items-center rounded-md px-3 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
          >
            Details
          </Link>
        </div>
      </div>
      {running && (
        <div className="bg-muted/30 border-t px-4 py-4">
          <RunForm workflow={job} />
        </div>
      )}
    </li>
  );
}

/** What starts a job when nobody presses anything, in a few words. */
function TriggerChip({ trigger }: { trigger: TriggerModel }) {
  const when = firesWhenShort(trigger);
  return (
    <Badge
      variant="outline"
      title={[firesWhen(trigger), trigger.disabled_reason].filter(Boolean).join(" — ")}
      className={cn("font-normal", trigger.enabled ? "text-brand" : "text-muted-foreground")}
    >
      {trigger.enabled ? when : `paused · ${when}`}
    </Badge>
  );
}

function Claims({
  term,
  claims,
}: {
  term: string;
  claims: { data?: KnowledgeEntry[]; isLoading: boolean; error: unknown };
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Known about “{term}”</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {claims.isLoading && <Skeleton className="h-20 w-full" />}
        {claims.error ? (
          <p className="text-destructive text-sm">That could not be searched.</p>
        ) : null}
        {claims.data?.length === 0 && (
          <p className="text-muted-foreground text-sm">Nothing known about that yet.</p>
        )}
        {claims.data?.map((entry) => (
          <div key={entry.id} className="space-y-1 border-t pt-2 first:border-t-0 first:pt-0">
            <p className="text-sm leading-snug">{entry.title}</p>
            <p className="text-muted-foreground font-mono text-xs break-all">{entry.key}</p>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant="outline" className="font-normal">
                {entry.kind}
              </Badge>
              <Badge
                variant={entry.evidence === "asserted" ? "outline" : "secondary"}
                className="font-normal"
              >
                {EVIDENCE[entry.evidence]?.label ?? entry.evidence}
              </Badge>
              {/* Where it came from decides whether it may drive a call at all. */}
              <span className="text-muted-foreground text-xs">from {entry.source}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function Known({
  summary,
}: {
  summary: {
    data?: {
      kind_counts: Record<string, number>;
      system_counts: Record<string, number>;
      evidence_counts: Record<string, number>;
    };
    isLoading: boolean;
  };
}) {
  if (summary.isLoading) return <Skeleton className="h-64 w-full" />;
  if (!summary.data) return null;

  const counts = summary.data.evidence_counts;
  const total = Object.values(summary.data.kind_counts).reduce((a, b) => a + b, 0);
  const systems = Object.entries(summary.data.system_counts).sort((a, b) => b[1] - a[1]);
  const levels = EVIDENCE_ORDER.filter((level) => counts[level]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">What is known</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <p className="text-3xl font-semibold tabular-nums">{total.toLocaleString()}</p>
          <p className="text-muted-foreground text-sm">
            {total === 1 ? "claim" : "claims"} about{" "}
            {systems.length === 1 ? "one system" : `${systems.length} systems`}
          </p>
        </div>

        {systems.length > 0 && (
          <ul className="space-y-1">
            {systems.map(([system, count]) => (
              <li key={system} className="flex items-baseline justify-between gap-3 text-xs">
                <span className="truncate font-mono" title={system}>
                  {hostOf(system)}
                </span>
                <span className="text-muted-foreground tabular-nums">{count}</span>
              </li>
            ))}
          </ul>
        )}

        {levels.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium">How firmly</p>
            {levels.map((level) => {
              const count = counts[level] ?? 0;
              const share = total ? Math.max(2, Math.round((count / total) * 100)) : 0;
              return (
                <div key={level} className="space-y-1">
                  <div className="flex items-baseline justify-between gap-3 text-xs">
                    <span className="font-medium">{EVIDENCE[level].label}</span>
                    <span className="text-muted-foreground tabular-nums">{count}</span>
                  </div>
                  <div className="bg-muted h-1.5 overflow-hidden rounded-full">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        level === "asserted" ? "bg-muted-foreground/50" : "bg-good",
                      )}
                      style={{ width: `${share}%` }}
                    />
                  </div>
                  <p className="text-muted-foreground text-xs">{EVIDENCE[level].meaning}</p>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
