"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getSummary, summaryKeys, type TaskLineModel } from "@/features/analytics/api";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const WINDOWS = [1, 7, 30] as const;

/** Everything here is derived from rows somebody can open. */
export function Overview() {
  const [days, setDays] = useState<number>(7);
  const summary = useQuery({
    queryKey: summaryKeys.window(days),
    queryFn: () => getSummary(days),
  });

  if (summary.isLoading) return <Skeleton className="h-96 w-full" />;
  if (summary.error) return <p className="text-destructive">{String(summary.error)}</p>;
  if (!summary.data) return null;

  const { watching, noticing, doing, tasks } = summary.data;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="text-muted-foreground text-sm">
            What has been watched, what the system noticed, and what it did about it.
          </p>
        </div>
        <div className="flex gap-1">
          {WINDOWS.map((window) => (
            <button
              key={window}
              type="button"
              onClick={() => setDays(window)}
              aria-pressed={days === window}
              // A near-white chip was the loudest thing on a page whose subject
              // is three numbers. Which window you are looking at is worth
              // marking, not worth shouting.
              className={`rounded-md border px-2 py-1 text-xs ${
                days === window
                  ? "bg-secondary text-foreground border-ring"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {window === 1 ? "24 hours" : `${window} days`}
            </button>
          ))}
        </div>
      </div>

      <section className="grid gap-3 sm:grid-cols-3">
        <Figure label="Hours of work watched" value={watching.hours.toString()}>
          {watching.events.toLocaleString()} events from {watching.devices}{" "}
          {watching.devices === 1 ? "browser" : "browsers"}
        </Figure>
        <Figure label="Tasks noticed" value={noticing.tasks.toString()}>
          jobs the miner found in what was watched
        </Figure>
        <Figure label="Runs" value={doing.runs.toString()}>
          {Object.entries(doing.outcomes)
            .map(([outcome, count]) => `${count} ${outcome}`)
            .join(" · ") || "none yet"}
          {doing.rehearsed > 0 && ` · ${doing.rehearsed} rehearsed`}
        </Figure>
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">What kind of work it is</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(noticing.by_kind).map(([kind, count]) => (
            <Badge key={kind} variant="secondary">
              {kind} · {count}
            </Badge>
          ))}
          {Object.keys(noticing.by_kind).length === 0 && (
            <p className="text-muted-foreground text-sm">
              Nothing noticed yet. Tasks appear once the same piece of work has been seen more than
              once.
            </p>
          )}
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Tasks</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>Steps</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task: TaskLineModel) => (
              <TableRow key={task.id}>
                <TableCell className="font-medium">
                  <Link href={`/jobs/${task.id}`} className="underline">
                    {task.title}
                  </Link>
                  <span className="text-muted-foreground block text-xs">{task.host}</span>
                </TableCell>
                <TableCell>{task.kind}</TableCell>
                <TableCell>{task.steps}</TableCell>
              </TableRow>
            ))}
            {tasks.length === 0 && (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  None yet — the system has nothing matching that.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>
    </div>
  );
}

function Figure({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-muted-foreground mt-1 text-xs">{children}</p>
    </div>
  );
}
