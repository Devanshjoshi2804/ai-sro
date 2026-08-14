"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { listRecordings, recordingKeys, type RecordingSummary } from "@/features/recording/api";
import { induceSkill } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  capturing: "default",
  sealed: "secondary",
  abandoned: "destructive",
};

export function RecordingList() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>([]);

  const recordings = useQuery({ queryKey: recordingKeys.all, queryFn: listRecordings });

  const induct = useMutation({
    mutationFn: () => induceSkill(selected[0], selected[1]),
    onSuccess: (result) => {
      toast.success(`Skill v${result.version} induced`, {
        description: `${result.step_count} steps, ${result.input_parameter_count} inputs`,
      });
      setSelected([]);
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
    onError: (error) =>
      toast.error("Induction failed", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (recordings.isLoading) return <Skeleton className="h-64 w-full" />;
  if (recordings.error) return <p className="text-destructive">{String(recordings.error)}</p>;

  const rows = recordings.data ?? [];

  // Induction diffs two runs of the same objective. Anything else would either
  // hardcode every value (same run twice) or align unrelated steps.
  const pairable = (row: RecordingSummary) =>
    row.status === "sealed" &&
    (selected.length === 0 ||
      rows.find((r) => r.id === selected[0])?.objective_key?.objective_type ===
        row.objective_key?.objective_type);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Recordings</h1>
          <p className="text-muted-foreground text-sm">
            Select two sealed runs of the same objective to induce a skill.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            disabled={selected.length !== 2 || induct.isPending}
            onClick={() => induct.mutate()}
          >
            {induct.isPending ? "Inducing…" : "Induce skill from 2 runs"}
          </Button>
          <Link href="/console">
            <Button>Teach a workflow</Button>
          </Link>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12" />
            <TableHead>Objective</TableHead>
            <TableHead>Label</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Frames</TableHead>
            <TableHead>Narration</TableHead>
            <TableHead>Started</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.id}>
              <TableCell>
                <input
                  type="checkbox"
                  aria-label={`Select recording ${row.id}`}
                  checked={selected.includes(row.id)}
                  disabled={!selected.includes(row.id) && (selected.length >= 2 || !pairable(row))}
                  onChange={(event) =>
                    setSelected((current) =>
                      event.target.checked
                        ? [...current, row.id]
                        : current.filter((id) => id !== row.id),
                    )
                  }
                />
              </TableCell>
              <TableCell>
                <Link href={`/recordings/${row.id}`} className="hover:underline">
                  {row.objective_key?.objective_type ?? "unnamed"}
                </Link>
                <span className="text-muted-foreground block text-xs">
                  {row.objective_key
                    ? `${row.objective_key.target_system} · ${row.objective_key.facility}`
                    : "named at seal"}
                </span>
              </TableCell>
              <TableCell>{row.label ?? "—"}</TableCell>
              <TableCell>
                <Badge variant={STATUS_VARIANT[row.status] ?? "outline"}>{row.status}</Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">{row.frame_count}</TableCell>
              <TableCell>{row.has_narration ? "yes" : "—"}</TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {new Date(row.started_at).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-muted-foreground py-12 text-center">
                No recordings yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
