"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listSkills, skillKeys, type SkillSummary } from "@/features/skill/api";
import { Rung } from "@/features/skill/components/ladder";
import { DataView } from "@/components/data-view";
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

  return (
    <DataView
      title="Skills"
      description="Induced from paired demonstrations. Review before promoting."
      loading={skills.isLoading}
      error={skills.error}
      rows={skills.data ?? []}
      // The name and what it is for, because a supervisor looking for one is
      // remembering the task rather than the system it runs against.
      matches={(skill: SkillSummary, term) =>
        `${skill.name} ${skill.summary ?? ""} ${skill.objective_key.target_system} ${
          skill.objective_key.facility
        }`
          .toLowerCase()
          .includes(term)
      }
      // Which rung, which is the question this page exists to answer.
      facet={{ name: "stage", of: (skill: SkillSummary) => skill.latest_stage }}
      empty={{
        line: "No skills yet.",
        hint: (
          <>
            A skill is induced from demonstrations of the same task.{" "}
            <Link href="/recordings" className="text-brand underline">
              Pair two recordings
            </Link>{" "}
            to make one.
          </>
        ),
      }}
    >
      {(shown) => (
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
            {shown.map((skill) => (
              <TableRow key={skill.id}>
                <TableCell>
                  <Link href={`/skills/${skill.id}`} className="hover:underline">
                    {skill.name}
                  </Link>
                  {skill.summary && (
                    <span className="text-muted-foreground block max-w-md truncate text-xs">
                      {skill.summary}
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {skill.objective_key.target_system} · {skill.objective_key.facility}
                </TableCell>
                <TableCell className="text-right tabular-nums">v{skill.latest_version}</TableCell>
                <TableCell>
                  <Rung stage={skill.latest_stage} />
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {new Date(skill.created_at).toLocaleDateString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </DataView>
  );
}
