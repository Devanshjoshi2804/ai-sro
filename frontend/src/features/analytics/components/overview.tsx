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

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  taught: "default",
  new: "secondary",
  dismissed: "outline",
};

/**
 * Everything here is derived from rows somebody can open. The one estimate is
 * labelled as one: time saved is what the task used to take, times the number
 * of times the system did it instead.
 */
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
              className={`rounded-md border px-2 py-1 text-xs ${
                days === window ? "bg-foreground text-background" : "text-muted-foreground"
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
          {noticing.worth_offering} worth offering · {noticing.taught} taught ·{" "}
          {noticing.dismissed} dismissed
        </Figure>
        <Figure label="Minutes saved" value={doing.minutes_saved.toString()} estimate>
          {doing.clean} clean · {doing.degraded} degraded · {doing.failed} failed ·{" "}
          {doing.withheld} rehearsed
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
              Nothing noticed yet. Tasks appear once the same piece of work has been seen more
              than once.
            </p>
          )}
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-sm font-medium">Tasks, by what they are worth</h2>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Task</TableHead>
              <TableHead>Seen</TableHead>
              <TableHead>Each takes</TableHead>
              <TableHead>Spent by hand</TableHead>
              <TableHead>Run for them</TableHead>
              <TableHead>Saved</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task: TaskLineModel) => (
              <TableRow key={`${task.host}:${task.title}`}>
                <TableCell className="font-medium">
                  {task.skill_id ? (
                    <Link href={`/skills/${task.skill_id}`} className="underline">
                      {task.title}
                    </Link>
                  ) : (
                    task.title
                  )}
                  <span className="text-muted-foreground block text-xs">{task.host}</span>
                </TableCell>
                <TableCell>{task.times_seen}×</TableCell>
                <TableCell>{task.median_seconds}s</TableCell>
                <TableCell>{task.minutes_spent} min</TableCell>
                <TableCell>{task.runs}</TableCell>
                <TableCell>{task.minutes_saved} min</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[task.status] ?? "outline"}>{task.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {tasks.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-muted-foreground">
                  None yet — the system has nothing matching that.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </section>

      <p className="text-muted-foreground text-xs">
        Minutes saved is an estimate built from one measurement: how long the task took the
        operator, times the number of runs that actually sent something. A rehearsal saved
        nobody anything and is not counted.
      </p>
    </div>
  );
}

function Figure({
  label,
  value,
  estimate = false,
  children,
}: {
  label: string;
  value: string;
  estimate?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-muted-foreground text-xs">
        {label}
        {estimate && <span className="ml-1">(estimated)</span>}
      </p>
      <p className="text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-muted-foreground mt-1 text-xs">{children}</p>
    </div>
  );
}
