"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataView } from "@/components/data-view";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  listBrowsers,
  restoreBrowser,
  revokeBrowser,
  rosterKeys,
  type DeviceLineModel,
} from "@/features/workflow/api";
import { when } from "@/features/workflow/format";

export function BrowserRoster() {
  const queryClient = useQueryClient();
  const browsers = useQuery({
    queryKey: rosterKeys.all,
    queryFn: listBrowsers,
    refetchInterval: 3000,
  });

  // One armed id for the whole list, cleared whenever the list changes at all.
  // In the rig this fell out of rebuilding the strip's DOM every three seconds;
  // here it has to be asked for. A per-row `useState` would keep an armed press
  // alive across a change that moved what the row means, which is the one thing
  // a control that cuts a browser off mid-shift must not do.
  const [armed, setArmed] = useState<string | null>(null);
  const shape = (browsers.data ?? [])
    .map((b) => `${b.device_id}:${b.online}:${b.revoked_at ?? ""}`)
    .join("|");
  // Adjusted during render rather than in an effect. An effect would disarm on
  // a second pass, which is one paint in which a stale armed button is on
  // screen and clickable -- and `react-hooks/set-state-in-effect` refuses it
  // for that reason.
  const [drawnFor, setDrawnFor] = useState(shape);
  if (shape !== drawnFor) {
    setDrawnFor(shape);
    setArmed(null);
  }

  // On the row, not in a toast: with several browsers a toast cannot say which
  // one refused.
  const [refusals, setRefusals] = useState<Record<string, string>>({});
  const say = (deviceId: string, error: unknown) =>
    setRefusals((prev) => ({
      ...prev,
      [deviceId]: error instanceof Error ? error.message : String(error),
    }));
  const forget = (deviceId: string) =>
    setRefusals((prev) => {
      if (!(deviceId in prev)) return prev;
      const rest = { ...prev };
      delete rest[deviceId];
      return rest;
    });

  const revoke = useMutation({
    // Wrapped: v5 hands the mutationFn a second `context` argument, and the
    // api helpers take exactly one.
    mutationFn: (deviceId: string) => revokeBrowser(deviceId),
    onSuccess: () => {
      toast.success("revoked — that browser will be refused");
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
    onError: (error, deviceId) => say(deviceId, error),
  });

  const restore = useMutation({
    mutationFn: (deviceId: string) => restoreBrowser(deviceId),
    onSuccess: () => {
      toast.success("restored — that browser can take part again");
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
    onError: (error, deviceId) => say(deviceId, error),
  });

  return (
    <DataView
      title="Browsers"
      description="A browser is a signed-in Chrome running the extension — the thing that actually drives a run against the warehouse."
      loading={browsers.isLoading}
      error={browsers.error}
      rows={browsers.data ?? []}
      empty={{
        line: "No browser has registered.",
        hint: "A browser appears here when somebody signs the extension in. Until one does, nothing can drive a run.",
      }}
    >
      {(shown) => (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Browser</TableHead>
              <TableHead>Last seen</TableHead>
              <TableHead>State</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((b: DeviceLineModel) => (
              <TableRow key={b.device_id}>
                <TableCell className={b.revoked_at ? "line-through" : undefined}>
                  <div>{b.label}</div>
                  <div className="text-muted-foreground font-mono text-xs">
                    {b.device_id} · {b.principal_id}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground font-mono text-xs">
                  {when(b.last_seen_at)}
                </TableCell>
                <TableCell>
                  {b.revoked_at ? (
                    <Badge variant="destructive">{`revoked ${when(b.revoked_at)}`}</Badge>
                  ) : b.online ? (
                    <Badge>online</Badge>
                  ) : (
                    <Badge variant="outline">offline</Badge>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {b.revoked_at ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        forget(b.device_id);
                        restore.mutate(b.device_id);
                      }}
                    >
                      restore
                    </Button>
                  ) : (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        forget(b.device_id);
                        if (armed !== b.device_id) return setArmed(b.device_id);
                        setArmed(null);
                        revoke.mutate(b.device_id);
                      }}
                    >
                      {armed === b.device_id ? "revoke — sure?" : "revoke"}
                    </Button>
                  )}
                  {refusals[b.device_id] && (
                    <p className="text-destructive mt-1 text-xs">{refusals[b.device_id]}</p>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </DataView>
  );
}
