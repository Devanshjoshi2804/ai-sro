"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getSkill, promoteSkill, skillKeys, type StepModel } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

/** v0 stops at shadow. The backend refuses anything beyond it regardless. */
const NEXT_STAGE: Record<string, string | undefined> = { recorded: "shadow" };

export function SkillDetail({ skillId }: { skillId: string }) {
  const queryClient = useQueryClient();

  const skill = useQuery({
    queryKey: skillKeys.detail(skillId),
    queryFn: () => getSkill(skillId),
  });

  const promote = useMutation({
    mutationFn: ({ version, to }: { version: number; to: string }) =>
      promoteSkill(skillId, version, to),
    onSuccess: (version) => {
      toast.success(`Promoted to ${version.stage}`);
      void queryClient.invalidateQueries({ queryKey: skillKeys.detail(skillId) });
    },
    onError: (error) =>
      toast.error("Promotion refused", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (skill.isLoading) return <Skeleton className="h-96 w-full" />;
  if (skill.error) return <p className="text-destructive">{String(skill.error)}</p>;
  if (!skill.data) return null;

  const latest = skill.data.versions.at(-1);
  const nextStage = latest ? NEXT_STAGE[latest.stage] : undefined;

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{skill.data.name}</h1>
          {latest?.summary && <p className="max-w-2xl text-sm">{latest.summary}</p>}
          {latest?.when_to_use && (
            <p className="text-muted-foreground max-w-2xl text-sm">{latest.when_to_use}</p>
          )}
          <p className="text-muted-foreground text-sm">
            {skill.data.objective_key.target_system} · {skill.data.objective_key.facility} ·{" "}
            {skill.data.objective_key.entity_type}
          </p>
        </div>
        {latest && (
          <div className="flex items-center gap-3">
            <Badge variant={latest.stage === "shadow" ? "default" : "outline"}>
              v{latest.version} · {latest.stage}
            </Badge>
            <Button
              disabled={!nextStage || promote.isPending}
              onClick={() =>
                nextStage && promote.mutate({ version: latest.version, to: nextStage })
              }
            >
              {nextStage ? `Promote to ${nextStage}` : "At highest permitted stage"}
            </Button>
          </div>
        )}
      </header>

      {latest && (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Provenance</CardTitle>
            </CardHeader>
            <CardContent className="text-muted-foreground space-y-1 text-sm">
              <p>
                Induced {new Date(latest.induced_at).toLocaleString()} by {latest.induced_by}
              </p>
              <p className="font-mono text-xs">{latest.recording_ids.join(" + ")}</p>
              <p>{latest.provenance_note}</p>
            </CardContent>
          </Card>

          <section className="space-y-2">
            <h2 className="text-lg font-medium">Parameters</h2>
            {latest.parameters.map((parameter) => (
              <div key={parameter.name} className="rounded-md border px-4 py-3 text-sm">
                <div className="flex items-center gap-3">
                  <code className="font-mono">${parameter.name}</code>
                  <Badge variant="secondary">{parameter.kind}</Badge>
                  {parameter.source_step_index !== null && (
                    <span className="text-muted-foreground text-xs">
                      from step {parameter.source_step_index}
                    </span>
                  )}
                </div>
                {parameter.observed_values.length > 0 && (
                  <p className="text-muted-foreground mt-1 text-xs">
                    Observed: {parameter.observed_values.join(" / ")}
                  </p>
                )}
              </div>
            ))}
            {latest.parameters.length === 0 && (
              <p className="text-muted-foreground text-sm">
                Nothing varied between the two runs, so every value is fixed.
              </p>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-medium">Steps</h2>
            {latest.steps.map((step) => (
              <StepCard key={step.index} step={step} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}

function StepCard({ step }: { step: StepModel }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-3 text-base">
          <span className="text-muted-foreground tabular-nums">#{step.index}</span>
          <span className="font-normal">{step.intent}</span>
          {step.requires_human && <Badge variant="destructive">needs a human</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {step.narration && (
          <blockquote className="border-muted text-muted-foreground border-l-2 pl-3 text-sm italic">
            “{step.narration}”
          </blockquote>
        )}
        {step.branch_hint && (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs">
            <span className="font-medium">Described but not demonstrated:</span>{" "}
            {step.branch_hint}
            <span className="text-muted-foreground block">
              Nothing was recorded doing this, so it is a question rather than a branch.
            </span>
          </div>
        )}
        {step.network_plan && (
          <div className="space-y-1">
            <p className="text-muted-foreground text-xs font-medium uppercase">Network plan</p>
            <p className="font-mono text-xs break-all">
              {step.network_plan.method} {step.network_plan.url}
            </p>
            {!step.network_plan.replayable && (
              <p className="text-destructive text-xs">
                Not replayable: {step.network_plan.unreplayable_reason}
              </p>
            )}
            {step.network_plan.required_credentials.length > 0 && (
              <p className="text-muted-foreground text-xs">
                Credentials: {step.network_plan.required_credentials.join(", ")}
              </p>
            )}
          </div>
        )}

        {step.network_plan && step.ui_plan && <Separator />}

        {step.ui_plan && (
          <div className="space-y-1">
            <p className="text-muted-foreground text-xs font-medium uppercase">UI plan</p>
            <p className="text-xs">
              {step.ui_plan.action} {step.ui_plan.target ?? ""}
              {step.ui_plan.value ? ` = ${step.ui_plan.value}` : ""}
            </p>
            {step.ui_plan.target_path && (
              <p className="text-muted-foreground font-mono text-xs">{step.ui_plan.target_path}</p>
            )}
          </div>
        )}

        {step.assertions.length > 0 && (
          <div className="space-y-1">
            <p className="text-muted-foreground text-xs font-medium uppercase">Assertions</p>
            {step.assertions.map((assertion, index) => (
              <p key={index} className="text-xs">
                {assertion.kind}
                {assertion.pointer ? ` ${assertion.pointer}` : ""} → {assertion.expected}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
