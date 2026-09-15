"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getKnowledgeSummary,
  knowledgeKeys,
  searchKnowledge,
  type KnowledgeEntry,
} from "@/features/knowledge/api";
import { OpenQuestions } from "@/features/knowledge/components/open-questions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * What the organisation knows.
 *
 * Teaching is not a conversation. One operator demonstrates a task and the
 * whole tenant has it — so this exists to make that visible: what is known,
 * how firmly, who taught it, and which claims the organisation's own runs have
 * proven since. A shared brain nobody can look at is indistinguishable from no
 * shared brain.
 */
const EVIDENCE_ORDER = ["round_trip", "reproduced", "observed", "asserted"];

const EVIDENCE_MEANING: Record<string, string> = {
  round_trip: "created, read back, changed and removed — all recorded",
  reproduced: "re-run and matched what was stored before",
  observed: "seen once, and the exchange was stored",
  asserted: "written down, with no stored exchange. Not evidence.",
};

export function KnowledgePage() {
  const [query, setQuery] = useState("");

  const summary = useQuery({ queryKey: knowledgeKeys.summary, queryFn: getKnowledgeSummary });
  const results = useQuery({
    queryKey: knowledgeKeys.search(query),
    queryFn: () => searchKnowledge(query),
    enabled: query.trim().length > 2,
  });

  if (summary.isLoading) return <Skeleton className="h-96 w-full" />;
  if (!summary.data) return null;

  const known = Object.values(summary.data.kind_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">What we know</h1>
        <p className="text-muted-foreground text-sm">
          Everything on this page is shared. One person teaches a task and the whole tenant has it;
          every verified run adds to what is known here.
        </p>
      </div>

      <OpenQuestions />

      <div className="grid gap-4 sm:grid-cols-3">
        <Figure
          label="claims"
          value={known}
          hint={Object.keys(summary.data.system_counts).join(", ")}
        />
        <Figure
          label="proved by our own runs"
          value={summary.data.learned_from_runs}
          hint="written back after a run verified — the number that says this is learning, not loading"
        />
        <Figure
          label="superseded"
          value={summary.data.superseded}
          hint="replaced by something better evidenced, and kept, because 'we used to believe this' explains an incident"
        />
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">How firmly</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {EVIDENCE_ORDER.filter((level) => summary.data.evidence_counts[level]).map((level) => (
            <div key={level} className="flex items-baseline gap-3">
              <span className="w-28 tabular-nums">{summary.data.evidence_counts[level]}</span>
              <Badge variant={level === "asserted" ? "outline" : "secondary"}>{level}</Badge>
              <span className="text-muted-foreground text-xs">{EVIDENCE_MEANING[level]}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <section className="space-y-2">
        <h2 className="text-lg font-medium">Taught by the team</h2>
        {summary.data.skills.map((skill) => (
          <div
            key={`${skill.skill_id}-${skill.version}`}
            className="flex flex-wrap items-center gap-3 rounded-md border px-4 py-3 text-sm"
          >
            {/* Not a link: `/skills/<id>` went with the pre-rig path. */}
            <span className="font-medium">{skill.name}</span>
            <span className="text-muted-foreground text-xs">
              v{skill.version} · {skill.system}/{skill.facility}
            </span>
            <Badge variant={skill.stage === "recorded" ? "outline" : "secondary"}>
              {skill.stage}
            </Badge>
            <span className="text-muted-foreground text-xs">taught by {skill.taught_by}</span>
            {skill.clean_streak > 0 && (
              <span className="text-xs">{skill.clean_streak} clean in a row</span>
            )}
            {skill.proposed_parameters > 0 && (
              <span className="text-muted-foreground text-xs">
                {/* One demonstration proposed these; a second would prove them. */}
                {skill.proposed_parameters} parameter
                {skill.proposed_parameters === 1 ? "" : "s"} still proposed
              </span>
            )}
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-medium">Ask it something</h2>
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="a screen, an endpoint, a field — “carrier”, “adjust”, “count”"
        />
        {results.data?.map((entry) => (
          <Entry key={entry.id} entry={entry} />
        ))}
        {query.trim().length > 2 && results.data?.length === 0 && (
          <p className="text-muted-foreground text-sm">Nothing known about that yet.</p>
        )}
      </section>
    </div>
  );
}

function Figure({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <Card>
      <CardContent className="space-y-1 pt-6">
        <p className="text-3xl font-semibold tabular-nums">{value.toLocaleString()}</p>
        <p className="text-sm">{label}</p>
        <p className="text-muted-foreground text-xs">{hint}</p>
      </CardContent>
    </Card>
  );
}

function Entry({ entry }: { entry: KnowledgeEntry }) {
  return (
    <div className="rounded-md border px-4 py-3 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <span>{entry.title}</span>
        <Badge variant="outline">{entry.kind}</Badge>
        <Badge variant={entry.evidence === "asserted" ? "outline" : "secondary"}>
          {entry.evidence}
        </Badge>
      </div>
      <p className="text-muted-foreground mt-1 font-mono text-xs break-all">{entry.key}</p>
      {/* Where it came from decides whether it may drive a call at all. */}
      <p className="text-muted-foreground text-xs">from {entry.source}</p>
    </div>
  );
}
