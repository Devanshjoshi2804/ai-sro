"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { startRecording, type StartRecordingRequest } from "@/features/recording/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/**
 * The five objective fields are all required, and equality between them is
 * exact — two runs only pair into a skill when every field matches. Free text
 * with no guidance produces "release_wave" and "Release Wave" as two different
 * objectives, so the field hints matter more than they look.
 */
const DIRECTIONS = ["outbound", "inbound", "internal"] as const;

type Form = {
  objective_type: string;
  target_system: string;
  entity_type: string;
  facility: string;
  direction: (typeof DIRECTIONS)[number];
  start_url: string;
  label: string;
};

const EMPTY: Form = {
  objective_type: "",
  target_system: "",
  entity_type: "",
  facility: "",
  direction: "outbound",
  start_url: "",
  label: "",
};

export function StartRecording() {
  const router = useRouter();
  const [form, setForm] = useState<Form>(EMPTY);

  const start = useMutation({
    mutationFn: () => {
      const body: StartRecordingRequest = {
        objective_key: {
          objective_type: form.objective_type.trim(),
          target_system: form.target_system.trim(),
          entity_type: form.entity_type.trim(),
          facility: form.facility.trim(),
          direction: form.direction,
        },
        start_url: form.start_url.trim() || null,
        label: form.label.trim() || null,
      };
      return startRecording(body);
    },
    onSuccess: (started) => {
      // Straight to the detail screen: it renders the live view while the
      // recording is open, so the operator lands where they demonstrate.
      router.push(`/recordings/${started.recording_id}`);
    },
    onError: (error) =>
      toast.error("Could not start the demonstration", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const required: (keyof Form)[] = ["objective_type", "target_system", "entity_type", "facility"];
  const complete = required.every((key) => form[key].trim().length > 0);

  const field = (key: keyof Form, label: string, placeholder: string, hint?: string) => (
    <div className="space-y-1.5">
      <Label htmlFor={key}>{label}</Label>
      <Input
        id={key}
        value={form[key]}
        placeholder={placeholder}
        onChange={(event) => setForm({ ...form, [key]: event.target.value })}
      />
      {hint && <p className="text-muted-foreground text-xs">{hint}</p>}
    </div>
  );

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Start a demonstration</h1>
        <p className="text-muted-foreground text-sm">
          A browser session opens and you drive it. Everything the page does is recorded.
          Demonstrate the same task twice to induce a skill.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Objective</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          {field("objective_type", "Objective", "release_wave", "What the task does.")}
          {field("target_system", "Target system", "blue_yonder", "The WMS being driven.")}
          {field("entity_type", "Entity", "wave", "What the task acts on.")}
          {field("facility", "Facility", "DC01")}

          <div className="space-y-1.5">
            <Label htmlFor="direction">Direction</Label>
            <Select
              value={form.direction}
              onValueChange={(value) => setForm({ ...form, direction: value as Form["direction"] })}
            >
              <SelectTrigger id="direction">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DIRECTIONS.map((direction) => (
                  <SelectItem key={direction} value={direction}>
                    {direction}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Session</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {field(
            "start_url",
            "Start URL",
            "https://wms.example.com/waves",
            "Optional. The session opens here instead of a blank page.",
          )}
          {field("label", "Label", "run 1", "Optional. Only to tell your runs apart.")}
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button disabled={!complete || start.isPending} onClick={() => start.mutate()}>
          {start.isPending ? "Opening a browser…" : "Start demonstration"}
        </Button>
        {!complete && (
          <p className="text-muted-foreground text-sm">
            All five objective fields are needed — two runs pair only when they match exactly.
          </p>
        )}
      </div>
    </div>
  );
}
