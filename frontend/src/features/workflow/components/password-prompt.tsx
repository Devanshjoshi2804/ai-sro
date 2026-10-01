"use client";

import { useId, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  answerRunPassword,
  getWorkflowRun,
  workflowRunKeys,
  type WorkflowRunModel,
} from "@/features/workflow/api";

/**
 * A Steel run that cannot sign in parks on a question naming the account. This
 * is where it is answered: the password goes to the backend's one door for it
 * (stored in the vault, or lent to this run alone) and nowhere else. The box
 * is uncontrolled, so the value lives in the input and in no state, is never
 * read back, and is emptied on the press.
 */
export function PasswordPrompt({ run, onSent }: { run: WorkflowRunModel; onSent: () => void }) {
  const box = useRef<HTMLInputElement>(null);
  // Several of these can stand in one thread, so the label cannot be one id.
  const field = useId();
  const asked = run.question;
  const send = useMutation({
    mutationFn: (body: { value: string; keep: boolean }) =>
      answerRunPassword(run.id, { question_id: asked?.id ?? "", ...body }),
    onSuccess: () => {
      toast.success("sent — the run carries on");
      onSent();
    },
    onError: (error) => toast.error("that could not be saved", { description: String(error) }),
  });
  if (run.outcome !== "running" || asked?.kind !== "password" || !asked.origin || !asked.username)
    return null;

  const press = (keep: boolean) => {
    const value = box.current?.value ?? "";
    if (box.current) box.current.value = "";
    if (value) send.mutate({ value, keep });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          This job needs your password for {asked.origin} ({asked.username})
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor={field}>Password</Label>
          <Input id={field} ref={box} type="password" autoComplete="off" />
        </div>
        <Button disabled={send.isPending} onClick={() => press(true)}>
          Save for next time
        </Button>
        <Button variant="outline" disabled={send.isPending} onClick={() => press(false)}>
          Just this once
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * The same box under the chat message a run posted for its password question.
 * It reads the run (the one record that knows whether that question still
 * stands) and draws only while this message's question is the standing one.
 */
export function RunPassword({ runId, questionId }: { runId: string; questionId: string }) {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: workflowRunKeys.detail(runId),
    queryFn: () => getWorkflowRun(runId),
    refetchInterval: (query) => (query.state.data?.outcome === "running" ? 2000 : false),
  });
  if (run.data?.question?.id !== questionId) return null;
  return (
    <PasswordPrompt
      run={run.data}
      onSent={() => queryClient.invalidateQueries({ queryKey: workflowRunKeys.detail(runId) })}
    />
  );
}
