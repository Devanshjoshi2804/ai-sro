"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  auditKeys,
  listWorkflows,
  readAudit,
  workflowKeys,
  type AuditResponse,
} from "@/features/workflow/api";
import { money, outcomeLabel, startOfToday, when } from "@/features/workflow/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** A section always renders: an empty one says `none` rather than vanishing. */
function Section({ heading, children }: { heading: string; children: React.ReactNode[] }) {
  return (
    <section className="space-y-1">
      <h3 className="text-sm font-medium">{heading}</h3>
      {children.length ? (
        children
      ) : (
        <p className="text-muted-foreground text-sm italic">none</p>
      )}
    </section>
  );
}

/**
 * The audit, four sections deep.
 *
 * The times are asymmetric on purpose: the picker and its heading are in the
 * reader's own zone, because a picker in UTC is unusable; every row is the
 * record's own UTC, because a row localised is no longer what the record says.
 */
export function AuditWalk() {
  const [since, setSince] = useState(() => startOfToday());

  // A half-typed datetime-local reads as garbage, and the door answers 422 to a
  // missing `since`. Neither is worth sending: fall back to midnight today.
  const safe = since && !Number.isNaN(Date.parse(since)) ? since : startOfToday();
  const iso = new Date(safe).toISOString();

  const audit = useQuery({
    queryKey: auditKeys.since(iso),
    queryFn: () => readAudit(iso),
    refetchInterval: 3000,
  });
  const workflows = useQuery({ queryKey: workflowKeys.all, queryFn: listWorkflows });

  const titleOf = (id: string | null) =>
    workflows.data?.find((w) => w.id === id)?.title ?? id ?? "";

  const a: AuditResponse | undefined = audit.data;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-4 pb-2">
        <CardTitle className="text-base">Audit</CardTitle>
        <div className="flex items-center gap-2">
          <Label htmlFor="since">since</Label>
          <Input
            id="since"
            type="datetime-local"
            className="w-auto"
            value={since}
            onChange={(e) => setSince(e.target.value)}
          />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {audit.error && <p className="text-destructive">{String(audit.error)}</p>}
        {a && (
          <>
            <Section heading={`runs since ${new Date(a.since).toLocaleString()}`}>
              {a.runs.map((r) => (
                <div key={r.id} className="space-y-0.5 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-brand font-mono">{when(r.started_at)}</span>
                    <span>{titleOf(r.workflow_id)}</span>
                    <span className="text-good">{outcomeLabel(r)}</span>
                    <span className="text-muted-foreground">
                      {`by ${r.started_by} on ${r.device_id}`}
                    </span>
                    <span className="font-mono">{money(r)}</span>
                    <Link className="underline" href={`/jobs/runs/${r.id}`}>
                      details
                    </Link>
                  </div>
                  {r.steps.map((s) => (
                    <div key={s.order} className="text-muted-foreground pl-4 text-xs">
                      <span>
                        {`${s.order} ${s.says} · ${s.verdict}`}
                        {s.verdict_by ? ` by ${s.verdict_by}` : ""}
                        {/* Only "sight". The audit words a weak match its own way. */}
                        {s.matched_by === "sight" ? " · found by sight" : ""}
                        {s.stale ? " · page moved" : ""}
                      </span>
                      {s.approved_at && (
                        <span className="text-brand">
                          {" "}
                          {/* `approved_by` is the browser that tapped, and the console
                              proves none: naming a person here would be an invention. */}
                          {`approved ${when(s.approved_at)}${
                            s.approved_by ? ` from ${s.approved_by}` : " by the tenant"
                          }`}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </Section>

            <Section heading="offers">
              {a.offers.map((o) => (
                <div key={o.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-brand font-mono">{when(o.at)}</span>
                  <span>{titleOf(o.workflow_id)}</span>
                  <span className="text-muted-foreground">
                    {`offered at ${o.k} on ${o.device_id}`}
                  </span>
                  <span>{String(o.fate).replace("_", " ")}</span>
                  {o.run_id && (
                    <Link className="underline" href={`/jobs/runs/${o.run_id}`}>
                      run
                    </Link>
                  )}
                </div>
              ))}
            </Section>

            <Section heading="chat">
              {a.chats.map((c) => (
                <div key={c.id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-brand font-mono">{when(c.at)}</span>
                  <span className="text-muted-foreground">chat · </span>
                  <span>{c.workflow_id ? titleOf(c.workflow_id) : "no job named"}</span>
                  {c.error && <span className="text-destructive">{c.error}</span>}
                  <span className="font-mono">{money(c)}</span>
                </div>
              ))}
            </Section>

            <Section heading="browsers">
              {a.devices.map((d) => (
                <div key={d.device_id} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-brand font-mono">{when(d.registered_at)}</span>
                  <span>
                    browser {d.device_id} registered
                  </span>
                  {d.revoked_at && (
                    <span className="text-destructive">{`revoked ${when(d.revoked_at)}`}</span>
                  )}
                </div>
              ))}
            </Section>
          </>
        )}
      </CardContent>
    </Card>
  );
}
