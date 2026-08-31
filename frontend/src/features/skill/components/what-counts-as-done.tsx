"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
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
import { addAssertion, skillKeys, type StepModel } from "@/features/skill/api";
import { ApiError } from "@/lib/api/client";

/**
 * Writing what counts as a step having worked.
 *
 * Post-conditions normally come out of the recordings — two demonstrations
 * answering the same status, or agreeing on a field. A step performed through
 * a connector has none behind it, so the only post-condition it can have is
 * one a person writes, and a write that proves nothing about its result keeps
 * the whole version off the top of the ladder.
 *
 * Written after a run rather than before one: an assertion invented before
 * anybody has seen what the tool answers is a guess about a document, and the
 * shadow rung exists precisely so somebody can look first.
 */
const READS_A_DOCUMENT = [
  { kind: "response_field_present", label: "the answer has a field", needsValue: false },
  { kind: "response_field_equals", label: "a field of the answer is", needsValue: true },
] as const;

const READS_AN_EXCHANGE = [
  { kind: "http_status", label: "the status is", needsValue: true, noPointer: true },
] as const;

export function WhatCountsAsDone({
  skillId,
  version,
  step,
}: {
  skillId: string;
  version: number;
  step: StepModel;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  // A tool answers a document: no status code, no screen. Offering a status
  // check on one would be offering a question nothing can ever answer, which
  // does not make the step safer -- it makes every run of it fail.
  const answersADocument = Boolean(step.tool_plan) && !step.network_plan;
  const choices = answersADocument
    ? READS_A_DOCUMENT
    : [...READS_A_DOCUMENT, ...READS_AN_EXCHANGE];

  const [kind, setKind] = useState<string>(choices[0].kind);
  const [pointer, setPointer] = useState("");
  const [expected, setExpected] = useState("");

  const chosen = choices.find((each) => each.kind === kind) ?? choices[0];
  const wantsPointer = !("noPointer" in chosen && chosen.noPointer);

  const write = useMutation({
    mutationFn: () =>
      addAssertion(skillId, {
        version,
        step_index: step.index,
        kind: kind as never,
        expected,
        pointer: wantsPointer ? pointer : null,
      }),
    onSuccess: () => {
      toast.success("Checked", {
        description:
          "A new version, at the bottom of the ladder — a streak earned before " +
          "this check existed is not evidence that it passes.",
      });
      setOpen(false);
      setPointer("");
      setExpected("");
      void queryClient.invalidateQueries({ queryKey: skillKeys.detail(skillId) });
    },
    onError: (error) =>
      toast.error("Not added", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  if (!open) {
    return (
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        Say what counts as done
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-md border p-3">
      <p className="text-muted-foreground text-xs">
        {answersADocument
          ? "Nobody demonstrated this call, so nothing here checks its answer yet — " +
            "and a step that changes something and proves nothing keeps this skill " +
            "off the top of the ladder. Run it in shadow first and write down what " +
            "the tool actually said."
          : "An extra check, beside the ones the demonstrations proved. It can only " +
            "tighten: nothing here removes what two runs agreed on."}
      </p>

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="space-y-1">
          <Label htmlFor={`kind-${step.index}`}>Check</Label>
          <Select value={kind} onValueChange={(value) => setKind(value ?? choices[0].kind)}>
            <SelectTrigger id={`kind-${step.index}`}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {choices.map((each) => (
                <SelectItem key={each.kind} value={each.kind}>
                  {each.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {wantsPointer && (
          <div className="space-y-1">
            <Label htmlFor={`pointer-${step.index}`}>Field</Label>
            <Input
              id={`pointer-${step.index}`}
              value={pointer}
              placeholder="/status"
              onChange={(event) => setPointer(event.target.value)}
            />
          </div>
        )}

        {chosen.needsValue && (
          <div className="space-y-1">
            <Label htmlFor={`expected-${step.index}`}>Is</Label>
            <Input
              id={`expected-${step.index}`}
              value={expected}
              placeholder="sent"
              onChange={(event) => setExpected(event.target.value)}
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          size="sm"
          disabled={
            write.isPending ||
            (wantsPointer && !pointer.trim()) ||
            (chosen.needsValue && !expected.trim())
          }
          onClick={() => write.mutate()}
        >
          Add this check
        </Button>
        <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
