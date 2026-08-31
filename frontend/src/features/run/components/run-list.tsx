"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listRuns, runKeys, type RunModel } from "@/features/run/api";
import { Badge } from "@/components/ui/badge";
import { DataView } from "@/components/data-view";
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

// `dark:` has to be spelled out: the primitive's own `dark:bg-destructive/20`
// outranks a plain utility, and this shipped for a moment as near-black text on
// a 20%-opacity red -- less legible than the tint it was meant to replace.
const STATUS_WEIGHT: Record<string, string> = {
  failed: "bg-destructive dark:bg-destructive text-background border-destructive font-semibold",
};

export function RunList() {
  const runs = useQuery({
    queryKey: runKeys.all,
    queryFn: listRuns,
    // A run in flight changes without anybody clicking.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((run: RunModel) => run.status === "running") ? 2000 : false,
  });

  return (
    <DataView
      title="Runs"
      description="Every attempt to perform a skill against a live system, and what each step actually did."
      loading={runs.isLoading}
      error={runs.error}
      rows={runs.data ?? []}
      // The skill and who stood behind it: the two things somebody looking for
      // a particular run actually remembers about it.
      matches={(run: RunModel, term) =>
        `${run.skill_id} ${run.stage} ${run.medium} ${run.authorized_by ?? ""}`
          .toLowerCase()
          .includes(term)
      }
      // The question this page exists to answer is "did anything fail", so the
      // filter that answers it is one press away.
      facet={{ name: "status", of: (run: RunModel) => run.status }}
      empty={{
        line: "Nothing has run yet.",
        hint: (
          <>
            A run happens when somebody asks for a taught task.{" "}
            <Link href="/console" className="text-brand underline">
              Ask for one in the console
            </Link>
            .
          </>
        ),
      }}
    >
      {(shown) => (
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
            {shown.map((run) => (
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
          </TableBody>
        </Table>
      )}
    </DataView>
  );
}
