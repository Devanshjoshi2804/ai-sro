"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listRuns, runKeys, type RunModel } from "@/features/run/api";
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

/**
 * Failure is the heavy mark, success the quiet one.
 *
 * The reverse shipped first — `succeeded` as a filled pill and `failed` as a
 * pale tint — and on the one page whose question is "is this still going well?"
 * the eye landed on every success and slid past every failure. A run that
 * worked is the expected case and does not need to be seen.
 */
const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  succeeded: "outline",
  running: "secondary",
  failed: "destructive",
};

const STATUS_WEIGHT: Record<string, string> = {
  failed: "bg-destructive text-background border-destructive font-semibold",
};

export function RunList() {
  const runs = useQuery({
    queryKey: runKeys.all,
    queryFn: listRuns,
    // A run in flight changes without anybody clicking.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((run: RunModel) => run.status === "running") ? 2000 : false,
  });

  if (runs.isLoading) return <Skeleton className="h-64 w-full" />;
  if (runs.error) return <p className="text-destructive">{String(runs.error)}</p>;

  const rows = runs.data ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
        <p className="text-muted-foreground text-sm">
          Every attempt to perform a skill against a live system, and what each step actually did.
        </p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Started</TableHead>
            <TableHead>Skill</TableHead>
            <TableHead>Stage</TableHead>
            <TableHead>Rung</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Authorised by</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((run) => (
            <TableRow key={run.id}>
              <TableCell>
                <Link href={`/runs/${run.id}`} className="hover:underline">
                  {new Date(run.started_at).toLocaleString()}
                </Link>
              </TableCell>
              <TableCell className="font-mono text-xs">
                {run.skill_id.slice(0, 12)} v{run.skill_version}
              </TableCell>
              <TableCell>
                <Badge variant="outline">{run.stage}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground text-sm">{run.medium}</TableCell>
              <TableCell>
                <Badge
                  variant={STATUS_VARIANT[run.status] ?? "outline"}
                  className={STATUS_WEIGHT[run.status]}
                >
                  {run.status}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {/* Blank is meaningful: a shadow run had nothing to authorise. */}
                {run.authorized_by ?? "—"}
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-muted-foreground py-12 text-center">
                Nothing has run yet. Ask for a task in the console.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
