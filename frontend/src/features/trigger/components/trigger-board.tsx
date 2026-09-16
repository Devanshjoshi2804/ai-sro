"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  createTrigger,
  deviceKeys,
  fireTrigger,
  listDevices,
  listTriggers,
  setTriggerEnabled,
  triggerKeys,
  type DeviceModel,
  type TriggerModel,
} from "@/features/trigger/api";
import { listWorkflows, workflowKeys, type WorkflowModel } from "@/features/workflow/api";
import { describe as describeCron, toCron, type Repeat } from "@/features/trigger/cron";
import { firesWhen } from "@/features/trigger/fires-when";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * What starts a job with nobody pressing anything.
 *
 * The board it replaces had the right facts in the wrong places. The schedule
 * column printed `arrival` and `0 7 * * 1-5` where a person needed "when
 * somebody opens the portal" and "every weekday at 07:00" -- the words already
 * existed, one component over, and were not used. Whether a trigger was on or
 * paused was readable only from which button it offered. And the form to make
 * one was always open underneath, three paragraphs of permissions long, so the
 * list of what is actually scheduled was the smaller half of its own page.
 *
 * Now: the list is the page, each row says in words what fires it and whether
 * it will, and the form opens when somebody asks for it.
 */
export function TriggerBoard() {
  const queryClient = useQueryClient();
  const triggers = useQuery({ queryKey: triggerKeys.all, queryFn: listTriggers });
  const devices = useQuery({ queryKey: deviceKeys.all, queryFn: listDevices });
  const jobs = useQuery({ queryKey: workflowKeys.all, queryFn: listWorkflows });
  const [creating, setCreating] = useState(false);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: triggerKeys.all });
  const complain = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : "That did not work");

  const enable = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setTriggerEnabled(id, enabled, enabled ? "" : "paused from the console"),
    onSuccess: (trigger) => {
      toast.success(trigger.enabled ? "Resumed" : "Paused — nothing will fire");
      void invalidate();
    },
    onError: complain,
  });

  const fire = useMutation({
    mutationFn: fireTrigger,
    onSuccess: () => {
      toast.success("Firing now, with the trigger’s own values and authorisation");
      void invalidate();
    },
    onError: complain,
  });

  const list = triggers.data ?? [];
  const active = list.filter((trigger) => trigger.enabled).length;
  // Nothing to look at yet, so the form is the page.
  const showForm = creating || (triggers.isSuccess && list.length === 0);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">Triggers</h1>
          <p className="text-muted-foreground max-w-2xl text-sm">
            What starts a job without anyone pressing Run — a time of day, or a page or mail an
            operator’s browser recognises. Every write still waits for a person until the job has
            earned the right to send unasked.
          </p>
        </div>
        {list.length > 0 && !creating && (
          <Button type="button" onClick={() => setCreating(true)}>
            New trigger
          </Button>
        )}
      </header>

      {showForm && (
        <NewTrigger
          jobs={jobs.data ?? []}
          devices={devices.data ?? []}
          onCreated={() => {
            setCreating(false);
            void invalidate();
          }}
          onCancel={list.length > 0 ? () => setCreating(false) : undefined}
          onError={complain}
        />
      )}

      <section aria-labelledby="scheduled-heading" className="space-y-3">
        {list.length > 0 && (
          <h2 id="scheduled-heading" className="flex items-baseline gap-2 text-lg font-medium">
            Scheduled
            <span className="text-muted-foreground text-sm font-normal tabular-nums">
              {active} active{list.length > active ? ` · ${list.length - active} paused` : ""}
            </span>
          </h2>
        )}

        {triggers.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : triggers.error ? (
          /* Said, rather than falling through to "nothing is scheduled" -- which
             is a claim about the schedule rather than about the request. */
          <div className="border-destructive/40 bg-destructive/10 rounded-lg border px-4 py-6">
            <p className="text-destructive text-sm font-medium">The triggers could not be read.</p>
            <p className="text-muted-foreground mt-1 font-mono text-xs">{String(triggers.error)}</p>
          </div>
        ) : list.length > 0 ? (
          <ul className="overflow-hidden rounded-lg border">
            {list.map((trigger) => (
              <Row
                key={trigger.id}
                trigger={trigger}
                jobs={jobs.data ?? []}
                devices={devices.data ?? []}
                onEnable={(enabled) => enable.mutate({ id: trigger.id, enabled })}
                onFire={() => fire.mutate(trigger.id)}
                busy={enable.isPending || fire.isPending}
              />
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}

function Row({
  trigger,
  jobs,
  devices,
  onEnable,
  onFire,
  busy,
}: {
  trigger: TriggerModel;
  jobs: WorkflowModel[];
  devices: DeviceModel[];
  onEnable: (enabled: boolean) => void;
  onFire: () => void;
  busy: boolean;
}) {
  // A job by its title, because that is the sentence the panel's offer says
  // and the one somebody recognises. Falling back to the id rather than to a
  // blank: a job re-mined away still has a trigger pointing at it, and the id
  // is what finds it in a log.
  const job = trigger.workflow_id ? jobs.find((j) => j.id === trigger.workflow_id) : undefined;
  const name = job?.title ?? trigger.workflow_id ?? trigger.skill_id ?? "Unknown";
  const browser = devices.find((device) => device.id === trigger.device_id)?.label;

  return (
    <li
      className={cn(
        "bg-card flex flex-col gap-3 border-b px-4 py-3 last:border-b-0 lg:flex-row lg:items-center",
        !trigger.enabled && "bg-muted/30",
      )}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {job ? (
            <Link
              href={`/jobs/${job.id}`}
              className="hover:text-brand font-medium underline-offset-4 hover:underline"
            >
              {name}
            </Link>
          ) : (
            <span className="font-medium">{name}</span>
          )}
          <Badge
            variant={trigger.enabled ? "secondary" : "outline"}
            className={cn("font-normal", trigger.enabled ? "text-good" : "text-muted-foreground")}
          >
            {trigger.enabled ? "Active" : "Paused"}
          </Badge>
        </div>
        <p className="text-sm">
          {firesWhen(trigger)}
          {trigger.kind === "schedule" && (
            <span className="text-muted-foreground"> · {trigger.timezone}</span>
          )}
        </p>
        <p className="text-muted-foreground flex flex-wrap gap-x-2 text-xs">
          {/* A browser's label is already a name for a browser -- "Macintosh ·
              Chrome" -- so "'s browser" after it read as nonsense. */}
          <span>{browser ? `in ${browser}` : "in the operator’s own browser"}</span>
          <span aria-hidden>·</span>
          {/* Two different permissions, and a line that blurred them would be a
              line that granted the wrong one. */}
          <span>
            {trigger.writes
              ? trigger.requires_confirmation
                ? "asks before it sends"
                : "sends without asking"
              : "reads only"}
          </span>
          {trigger.writes && trigger.authorized_by && (
            <>
              <span aria-hidden>·</span>
              <span>{trigger.authorized_by} stands behind it</span>
            </>
          )}
          {trigger.may_take_focus && (
            <>
              <span aria-hidden>·</span>
              <span>may bring its tab to the front</span>
            </>
          )}
        </p>
        {!trigger.enabled && trigger.disabled_reason && (
          <p className="text-warn text-xs">{trigger.disabled_reason}</p>
        )}
      </div>

      <div className="text-muted-foreground shrink-0 text-xs whitespace-nowrap lg:text-right">
        {trigger.last_fired_at ? (
          <>
            Last fired{" "}
            <time dateTime={trigger.last_fired_at} className="text-foreground tabular-nums">
              {new Date(trigger.last_fired_at).toLocaleString(undefined, {
                dateStyle: "medium",
                timeStyle: "short",
              })}
            </time>
          </>
        ) : (
          "Never fired"
        )}
      </div>

      <div className="flex shrink-0 gap-2">
        <Button variant="outline" size="sm" disabled={busy} onClick={onFire}>
          Fire now
        </Button>
        <Button
          variant={trigger.enabled ? "ghost" : "default"}
          size="sm"
          disabled={busy}
          onClick={() => onEnable(!trigger.enabled)}
        >
          {trigger.enabled ? "Pause" : "Resume"}
        </Button>
      </div>
    </li>
  );
}

function zones(): string[] {
  // The browser's own list, so a timezone is chosen rather than typed: a
  // misspelt zone is a schedule that fires at the wrong hour and says nothing.
  const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
  return intl.supportedValuesOf?.("timeZone") ?? ["UTC"];
}

function NewTrigger({
  jobs,
  devices,
  onCreated,
  onCancel,
  onError,
}: {
  jobs: WorkflowModel[];
  devices: DeviceModel[];
  onCreated: () => void;
  onCancel?: () => void;
  onError: (error: unknown) => void;
}) {
  const [jobId, setJobId] = useState("");
  const [repeat, setRepeat] = useState<Repeat>("weekdays");
  const [at, setAt] = useState("07:00");
  const [weekday, setWeekday] = useState(1);
  const [written, setWritten] = useState("0 7 * * 1-5");
  const cron = repeat === "custom" ? written : toCron(repeat, at, weekday);
  const inWords = cron ? describeCron(cron) : null;
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  // A job is a recording of somebody's own window, so it runs in a browser and
  // never on the server -- there is no choice to offer, only which browser.
  const [chosenDevice, setDeviceId] = useState("");
  // Derived, not seeded into state: the devices request can land after this
  // form mounts, and a default read once at mount would stay empty for good.
  const deviceId = chosenDevice || (devices.length === 1 ? devices[0].id : "");
  const [authorized, setAuthorized] = useState(false);
  const [autoApprove, setAutoApprove] = useState(false);
  const [mayTakeFocus, setMayTakeFocus] = useState(false);

  // Derived beside the disabled condition it explains, so the two cannot drift.
  const missing = [
    !jobId && "a job",
    !cron && "a time",
    !deviceId && "a browser",
    !authorized && "your name behind it",
  ].filter(Boolean) as string[];

  const create = useMutation({
    mutationFn: createTrigger,
    onSuccess: () => {
      toast.success("Scheduled");
      onCreated();
    },
    onError,
  });

  return (
    <section
      aria-labelledby="new-trigger-heading"
      className="bg-card max-w-3xl rounded-lg border p-5"
    >
      <h2 id="new-trigger-heading" className="text-lg font-medium">
        Put a job on a schedule
      </h2>

      <form
        className="mt-4 grid gap-5"
        onSubmit={(event) => {
          event.preventDefault();
          if (missing.length) return;
          create.mutate({
            skill_id: null,
            workflow_id: jobId,
            // Named rather than defaulted: the generated type has no defaults,
            // and a schedule that ran as a manual trigger would never fire.
            kind: "schedule",
            medium: "ui",
            device_id: deviceId,
            cron,
            timezone,
            authorized_by: authorized,
            auto_approve: autoApprove,
            may_take_focus: mayTakeFocus,
            // A question read out of a mail is a watch, marked on an open mail
            // in the operator's own browser -- not something this form makes.
            asks: false,
          });
        }}
      >
        <div className="grid gap-2">
          <Label htmlFor="job">Job</Label>
          <select
            id="job"
            required
            className="border-input bg-background h-9 rounded-md border px-3 text-sm"
            value={jobId}
            onChange={(event) => setJobId(event.target.value)}
          >
            <option value="">Choose a job</option>
            {[...jobs]
              .sort((a, b) => a.title.localeCompare(b.title))
              .map((job) => (
                <option key={job.id} value={job.id}>
                  {job.title}
                </option>
              ))}
          </select>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="grid content-start gap-2">
            <Label htmlFor="repeat">When</Label>
            <div className="flex gap-2">
              <select
                id="repeat"
                className="border-input bg-background h-9 min-w-0 flex-1 rounded-md border px-3 text-sm"
                value={repeat}
                onChange={(event) => setRepeat(event.target.value as Repeat)}
              >
                <option value="weekdays">Every weekday</option>
                <option value="daily">Every day</option>
                <option value="weekly">Every week on</option>
                <option value="custom">A cron expression</option>
              </select>
              {repeat === "weekly" && (
                <select
                  aria-label="Day"
                  className="border-input bg-background h-9 rounded-md border px-3 text-sm"
                  value={weekday}
                  onChange={(event) => setWeekday(Number(event.target.value))}
                >
                  {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day, index) => (
                    <option key={day} value={index}>
                      {day}
                    </option>
                  ))}
                </select>
              )}
              {repeat !== "custom" && (
                <Input
                  aria-label="Time"
                  type="time"
                  className="w-28"
                  value={at}
                  onChange={(event) => setAt(event.target.value)}
                />
              )}
            </div>
            {repeat === "custom" && (
              <Input
                aria-label="Cron expression"
                className="font-mono"
                value={written}
                onChange={(event) => setWritten(event.target.value)}
              />
            )}
            {/* What is about to be saved, in both languages: the expression
                because somebody will copy it, the words because `0 7 * * 1-5`
                firing on Sundays is a typo nobody can see. */}
            <p className="text-muted-foreground text-xs">
              {cron ? (
                <>
                  {inWords ?? "The scheduler will read this; it cannot be put in words"}{" "}
                  <code className="bg-muted rounded px-1">{cron}</code>
                </>
              ) : (
                "Give it a time to run at"
              )}
            </p>
          </div>

          <div className="grid content-start gap-2">
            <Label htmlFor="timezone">Time zone</Label>
            <select
              id="timezone"
              className="border-input bg-background h-9 rounded-md border px-3 text-sm"
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            >
              {zones().map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
            <p className="text-muted-foreground text-xs">
              The warehouse’s, not the server’s — so seven is seven in March and in November.
            </p>
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="device">Browser</Label>
          <select
            id="device"
            className="border-input bg-background h-9 rounded-md border px-3 text-sm"
            value={deviceId}
            onChange={(event) => {
              setDeviceId(event.target.value);
              if (!event.target.value) setMayTakeFocus(false);
            }}
          >
            <option value="">Choose a browser</option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.label}
              </option>
            ))}
          </select>
          <p className="text-muted-foreground text-xs">
            A job runs in an operator’s own browser, with their session, and only while that browser
            is connected.
          </p>
        </div>

        {/* Three separate permissions, deliberately three checkboxes. Each is a
            different thing to regret at three in the morning, and one "enable
            automation" switch would grant all three. */}
        <fieldset className="grid gap-3">
          <legend className="mb-1 text-sm font-medium">Permissions</legend>
          <Permission
            id="authorized"
            checked={authorized}
            onChange={setAuthorized}
            label="I stand behind every run this starts"
            note="Your name is what the record shows for a write nobody watched."
          />
          <Permission
            id="auto-approve"
            checked={autoApprove}
            onChange={setAutoApprove}
            label="Send writes without asking"
            note="Otherwise each run stops at its first write and waits for a person in the panel."
          />
          <Permission
            id="may-take-focus"
            checked={mayTakeFocus}
            onChange={setMayTakeFocus}
            disabled={!deviceId}
            label="May bring its tab to the front"
            note="Leave off for anything that fires while nobody is at the screen."
          />
        </fieldset>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={missing.length > 0 || create.isPending}>
            {create.isPending ? "Scheduling…" : "Schedule it"}
          </Button>
          {onCancel && (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
          {/* A disabled control that does not say what it is waiting for is a
              control people work around. */}
          {missing.length > 0 && (
            <p className="text-muted-foreground text-xs">Still needs {missing.join(", ")}.</p>
          )}
        </div>
      </form>
    </section>
  );
}

function Permission({
  id,
  checked,
  onChange,
  label,
  note,
  disabled = false,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  note: string;
  disabled?: boolean;
}) {
  return (
    <div className={cn("flex gap-3", disabled && "opacity-60")}>
      <input
        id={id}
        type="checkbox"
        className="accent-brand mt-1 size-4"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <div className="space-y-0.5">
        <Label htmlFor={id}>{label}</Label>
        <p className="text-muted-foreground text-xs">{note}</p>
      </div>
    </div>
  );
}
