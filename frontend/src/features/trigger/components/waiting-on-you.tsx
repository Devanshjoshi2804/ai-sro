"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  approveConfirmation,
  confirmationKeys,
  declineConfirmation,
  listConfirmations,
  type Confirmation,
} from "@/features/trigger/api";
import { ApiError } from "@/lib/api/client";

/**
 * Fires waiting for somebody to say yes.
 *
 * A manual trigger needs none of this — the click that fires it is the
 * confirmation. A schedule and an inbound message both go off with nobody
 * there, and until this queue existed a write on one of those could not be
 * created at all.
 *
 * What the screen has to make obvious is what pressing the button costs: the
 * run starts now, it writes to the warehouse, and it carries the name of the
 * person who pressed rather than the person who set the trigger up.
 */
export function WaitingOnYou() {
  const queryClient = useQueryClient();
  const waiting = useQuery({
    queryKey: confirmationKeys.all,
    queryFn: listConfirmations,
    // A card that arrives while somebody is looking at the screen is the whole
    // point of the queue; one that arrives while they are not is why it exists.
    refetchInterval: 15_000,
  });

  if (waiting.isLoading) return <Skeleton className="h-64 w-full" />;
  if (waiting.error) {
    return (
      <p className="text-destructive text-sm">
        {waiting.error instanceof ApiError
          ? waiting.error.problem.detail
          : String(waiting.error)}
      </p>
    );
  }

  const items = waiting.data ?? [];

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Waiting on you <span className="text-muted-foreground">({items.length})</span>
        </h1>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Each of these is a write that fired with nobody there. Nothing has run: approving
          one starts it now, with your name on the run. Nothing here runs because time
          passes — an unanswered card expires, and the trigger fires again if it is still
          true.
        </p>
      </header>

      {items.length === 0 ? (
        <p className="text-muted-foreground py-12 text-center text-sm">
          Nothing is waiting. A schedule or a mail that fires a write will put a card here.
        </p>
      ) : (
        items.map((item) => (
          <Waiting
            key={item.id}
            item={item}
            onAnswered={() =>
              void queryClient.invalidateQueries({ queryKey: confirmationKeys.all })
            }
          />
        ))
      )}
    </div>
  );
}

function Waiting({ item, onAnswered }: { item: Confirmation; onAnswered: () => void }) {
  const [declining, setDeclining] = useState(false);
  const [note, setNote] = useState("");

  const answer = useMutation({
    mutationFn: (yes: boolean) =>
      yes ? approveConfirmation(item.id) : declineConfirmation(item.id, note),
    onSuccess: (_, yes) => {
      toast.success(yes ? "Started" : "Declined", {
        description: yes
          ? "The run is going now, with your name on it."
          : "Nothing ran. What you turned down is kept — it is the clearest evidence there is about a trigger that should not exist.",
      });
      onAnswered();
    },
    onError: (error) =>
      toast.error("Not answered", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const runsOutAt = new Date(item.expires_at);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex flex-wrap items-center gap-3 text-base">
          <span className="font-normal">{item.skill_name || item.skill_id}</span>
          {/* Not a countdown, and not tinted by how near it is: reading the
              clock while rendering makes this component impure, and a colour
              that changed under somebody mid-decision would be pressure rather
              than information. The time is the information. */}
          <Badge variant="outline" className="font-normal">
            answerable until {runsOutAt.toLocaleString()}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">{item.because}</p>

        {Object.keys(item.values).length > 0 && (
          <div className="rounded-md border">
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(item.values).map(([name, value]) => (
                  <tr key={name} className="border-b last:border-0">
                    <td className="text-muted-foreground w-56 px-3 py-1.5">
                      <code className="font-mono">${name}</code>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-xs break-all">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Frozen when it was asked, and said so: a trigger edited since
                would otherwise turn a yes to one thing into a yes to another,
                under the name of whoever pressed the button. */}
            <p className="text-muted-foreground px-3 py-1.5 text-xs">
              What it would run with, as it was when this fired.
            </p>
          </div>
        )}

        {declining ? (
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={note}
              placeholder="why not? (optional)"
              className="max-w-sm"
              onChange={(event) => setNote(event.target.value)}
            />
            <Button
              variant="destructive"
              size="sm"
              disabled={answer.isPending}
              onClick={() => answer.mutate(false)}
            >
              Decline
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setDeclining(false)}>
              Cancel
            </Button>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" disabled={answer.isPending} onClick={() => answer.mutate(true)}>
              Run it now
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setDeclining(true)}>
              Decline
            </Button>
            <span className="text-muted-foreground text-xs">
              This writes to the warehouse, and the run will carry your name.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
