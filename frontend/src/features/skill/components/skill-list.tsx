"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listSkills, skillKeys } from "@/features/skill/api";
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

export function SkillList() {
  const skills = useQuery({ queryKey: skillKeys.all, queryFn: listSkills });

  if (skills.isLoading) return <Skeleton className="h-64 w-full" />;
  if (skills.error) return <p className="text-destructive">{String(skills.error)}</p>;

  const rows = skills.data ?? [];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Skills</h1>
        <p className="text-muted-foreground text-sm">
          Induced from paired demonstrations. Review before promoting.
        </p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Objective</TableHead>
            <TableHead className="text-right">Version</TableHead>
            <TableHead>Stage</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((skill) => (
            <TableRow key={skill.id}>
              <TableCell>
                <Link href={`/skills/${skill.id}`} className="hover:underline">
                  {skill.name}
                </Link>
              </TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {skill.objective_key.target_system} · {skill.objective_key.facility}
              </TableCell>
              <TableCell className="text-right tabular-nums">v{skill.latest_version}</TableCell>
              <TableCell>
                <Badge variant={skill.latest_stage === "shadow" ? "default" : "outline"}>
                  {skill.latest_stage}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground text-sm">
                {new Date(skill.created_at).toLocaleDateString()}
              </TableCell>
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} className="text-muted-foreground py-12 text-center">
                No skills yet. Pair two recordings to induce one.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
