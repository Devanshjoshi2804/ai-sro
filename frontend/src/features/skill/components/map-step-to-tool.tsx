"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  listOfferedTools,
  mapStepToTool,
  skillKeys,
  type ParameterModel,
  type StepModel,
} from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";

/**
 * Saying that a click is a tool call.
 *
 * The one part of a skill nobody demonstrates: induction reads recordings, and
 * a recording holds gestures and the calls they made. So this is a decision,
 * and the form is written to make the two things a person is actually deciding
 * obvious — which tool, and whether calling it changes anything.
 *
 * It matters because a gesture step can never reach `CLEAN`, so a skill whose
 * mail half is clicks is assisted forever. This is the screen that lifts that.
 */
export function MapStepToTool({
  skillId,
  version,
  step,
  parameters,
}: {
  skillId: string;
  version: number;
  step: StepModel;
  parameters: ParameterModel[];
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [server, setServer] = useState("");
  const [tool, setTool] = useState("");
  const [writes, setWrites] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});

  const offered = useQuery({
    queryKey: skillKeys.tools(server),
    queryFn: () => listOfferedTools(server),
    // Only once somebody has named a connector: there is nothing to ask before
    // that, and a request for the empty string is a 404 nobody learns from.
    enabled: open && server.trim().length > 0,
    retry: false,
  });

  const map = useMutation({
    mutationFn: () =>
      mapStepToTool(skillId, {
        version,
        step_index: step.index,
        server,
        tool,
        arguments: values,
        writes,
      }),
    onSuccess: () => {
      toast.success("Mapped", {
        description:
          "A new version, at the bottom of the ladder — this step now goes " +
          "through a door nobody has watched it go through.",
      });
      setOpen(false);
      void queryClient.invalidateQueries({ queryKey: skillKeys.detail(skillId) });
    },
    onError: (error) => {
      // What the refusal said, not a generic failure: every one of them names
      // the thing to fix — a tool the connector does not offer, a parameter
      // that does not exist, no connector configured at all.
      toast.error("Not mapped", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      });
    },
  });

  if (step.tool_plan) {
    return (
      <p className="text-muted-foreground text-xs">
        Performed by calling <code className="font-mono">{step.tool_plan.tool}</code> on{" "}
        <code className="font-mono">{step.tool_plan.server}</code>
        {step.tool_plan.writes ? " — it writes" : " — it reads"}.
      </p>
    );
  }

  if (!open) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        Perform this as a call
      </Button>
    );
  }

  const chosen = offered.data?.find((each) => each.name === tool);

  return (
    <div className="space-y-3 rounded-md border p-3">
      <p className="text-muted-foreground text-xs">
        A step performed by clicking can never be clean, so a skill with one in it stays
        assisted however well it runs. Mapping it onto a tool is what lifts that — and it
        is a decision with your name on it, because nobody demonstrated the call.
      </p>

      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor={`server-${step.index}`}>Connector</Label>
          <Input
            id={`server-${step.index}`}
            value={server}
            placeholder="mail"
            onChange={(event) => {
              setServer(event.target.value);
              setTool("");
            }}
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor={`tool-${step.index}`}>Tool</Label>
          {offered.error ? (
            <p className="text-destructive text-xs">
              {offered.error instanceof ApiError
                ? offered.error.problem.detail
                : String(offered.error)}
            </p>
          ) : (
            <Select
              value={tool}
              onValueChange={(value) => setTool(value ?? "")}
              disabled={!offered.data?.length}
            >
              <SelectTrigger id={`tool-${step.index}`}>
                <SelectValue
                  placeholder={
                    offered.isFetching ? "asking the connector…" : "what it offers"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {(offered.data ?? []).map((each) => (
                  <SelectItem key={each.name} value={each.name}>
                    {each.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {chosen && (
        <div className="space-y-2">
          {chosen.description && (
            <p className="text-muted-foreground text-xs">{chosen.description}</p>
          )}
          {chosen.arguments.map((name) => (
            <div key={name} className="space-y-1">
              <Label htmlFor={`arg-${step.index}-${name}`}>{name}</Label>
              <Input
                id={`arg-${step.index}-${name}`}
                value={values[name] ?? ""}
                placeholder="a value, or ${parameter}"
                onChange={(event) =>
                  setValues({ ...values, [name]: event.target.value })
                }
              />
            </div>
          ))}
          {parameters.length > 0 && (
            <p className="text-muted-foreground text-xs">
              This skill takes{" "}
              {parameters.map((parameter) => (
                <button
                  key={parameter.name}
                  type="button"
                  className="mr-1 font-mono underline"
                  onClick={() =>
                    navigator.clipboard?.writeText(`\${${parameter.name}}`).catch(() => {})
                  }
                >
                  ${parameter.name}
                </button>
              ))}
              — click one to copy it.
            </p>
          )}
        </div>
      )}

      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          checked={writes}
          onChange={(event) => setWrites(event.target.checked)}
          className="mt-1"
        />
        <span>
          Calling this changes something outside this system.
          <span className="text-muted-foreground block text-xs">
            Nothing else can tell us: a tool named <code className="font-mono">send</code>{" "}
            is a name, not a promise. Said here, it is never sent twice, it needs an
            assertion before this skill can run unattended, and it is withheld below the
            assisted rung.
          </span>
        </span>
      </label>

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          disabled={!server.trim() || !tool || map.isPending}
          onClick={() => map.mutate()}
        >
          Map this step
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Badge variant="outline" className="text-xs font-normal">
          makes a new version
        </Badge>
      </div>
    </div>
  );
}
