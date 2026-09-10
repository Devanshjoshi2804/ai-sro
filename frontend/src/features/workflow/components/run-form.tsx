"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  listBrowsers,
  rosterKeys,
  startWorkflowRun,
  type WorkflowModel,
} from "@/features/workflow/api";

/**
 * The mined parameter as the wire carries it. `WorkflowModel.parameters` is
 * generated as a bag of unknowns, so the narrowing happens here once rather
 * than at every read.
 */
type Parameter = { name: string; seen_values: string[] };

/**
 * The control that starts a real Chrome doing real work in a warehouse.
 *
 * Two properties earn their place over a smaller form. `live` is unticked:
 * the first press of a mined job reads everything and sends nothing, and a
 * default of true is a write nobody asked for. And the started run is followed
 * by `id` -- the field `POST /v1/workflow-runs` actually answers with. Reading
 * `run_id` there cost phase 5 a defect where a started run could never be
 * polled and its approval could never be reached; nothing threw, the run was
 * simply lost.
 */
export function RunForm({ workflow }: { workflow: WorkflowModel }) {
  const router = useRouter();
  const parameters = workflow.parameters as unknown as Parameter[];

  const browsers = useQuery({ queryKey: rosterKeys.all, queryFn: listBrowsers });
  // A revoked browser is on the roster so it can be restored, not so it can be
  // handed a run.
  const usable = (browsers.data ?? []).filter((b) => !b.revoked_at);

  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(parameters.map((p) => [p.name, p.seen_values.at(-1) ?? ""])),
  );
  // Empty until a person picks, so the first usable browser can become the
  // default the moment the roster lands without an effect to sync it.
  const [picked, setPicked] = useState("");
  const [live, setLive] = useState(false);
  const [refusal, setRefusal] = useState("");

  const deviceId = picked || usable[0]?.device_id || "";

  const start = useMutation({
    // Wrapped, not passed bare: v5 calls `mutationFn` with `(variables,
    // context)`, so a helper handed over directly receives an argument it
    // never declared the day it grows a second parameter.
    mutationFn: (body: Parameters<typeof startWorkflowRun>[0]) => startWorkflowRun(body),
    onSuccess: (run) => router.push(`/jobs/runs/${run.id}`),
  });

  // Nothing to draw until the roster says whether anything could drive a run:
  // a start button that is enabled for a moment and then is not is a press
  // that lands on an empty device id.
  if (browsers.isPending) return <Skeleton className="h-40 w-full" />;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    // Trimmed, because a client code pasted with a trailing space gets typed
    // into somebody's warehouse form with a trailing space.
    const trimmed = Object.fromEntries(
      parameters.map((p) => [p.name, (values[p.name] ?? "").trim()]),
    );
    // `required` stops an empty field but not three spaces, and the route
    // counts " " as given. Same refusal, same words, one round trip saved.
    const blank = parameters.map((p) => p.name).filter((name) => !trimmed[name]);
    if (blank.length) {
      setRefusal(`this job needs a value for: ${blank.join(", ")}`);
      return;
    }
    setRefusal("");
    start.mutate({ workflow_id: workflow.id, device_id: deviceId, values: trimmed, live });
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-lg border p-3">
      {parameters.map((p) => (
        <div key={p.name} className="space-y-1">
          <Label htmlFor={`${workflow.id}-${p.name}`}>{p.name}</Label>
          <Input
            id={`${workflow.id}-${p.name}`}
            list={`${workflow.id}-${p.name}-seen`}
            required
            value={values[p.name] ?? ""}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, [p.name]: event.target.value }))
            }
          />
          {/* The values a recording actually carried, so an operator can pick
              one they have used before instead of retyping it. */}
          <datalist id={`${workflow.id}-${p.name}-seen`}>
            {p.seen_values.map((seen) => (
              <option key={seen} value={seen} />
            ))}
          </datalist>
        </div>
      ))}

      <div className="space-y-1">
        <Label htmlFor={`${workflow.id}-browser`}>browser</Label>
        {usable.length === 0 ? (
          <p className="text-muted-foreground text-sm">no browser is connected</p>
        ) : (
          <select
            id={`${workflow.id}-browser`}
            value={deviceId}
            onChange={(event) => setPicked(event.target.value)}
            className="border-input h-9 w-full rounded-lg border bg-transparent px-3 text-sm"
          >
            {usable.map((b) => (
              <option key={b.device_id} value={b.device_id}>
                {`${b.label} · ${b.device_id}`}
              </option>
            ))}
          </select>
        )}
      </div>

      <Label htmlFor={`${workflow.id}-live`} className="text-sm">
        <input
          id={`${workflow.id}-live`}
          type="checkbox"
          checked={live}
          onChange={(event) => setLive(event.target.checked)}
        />
        live — send the writes
      </Label>

      <div className="flex items-center gap-2">
        <Button type="submit" size="sm" disabled={!deviceId || start.isPending}>
          {start.isPending ? "starting…" : "start"}
        </Button>
        {!live && <span className="text-muted-foreground text-xs">reads only</span>}
      </div>

      {refusal && <p className="text-destructive text-sm">{refusal}</p>}
      {/* Said, not swallowed: a refused start that looks like a started one is
          an operator waiting on a run that does not exist. */}
      {start.error && (
        <p className="text-destructive text-sm">{(start.error as Error).message}</p>
      )}
    </form>
  );
}
