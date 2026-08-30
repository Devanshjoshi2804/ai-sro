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
import { listSkills, skillKeys } from "@/features/skill/api";
import { describe as describeCron, toCron, type Repeat } from "@/features/trigger/cron";
import { ApiError } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

/**
 * What runs on a clock, and what each of those decisions costs.
 *
 * Every field here is refusable now rather than at three in the morning: a
 * skill nobody rehearsed, a value nobody supplied, a write with nobody's name
 * behind it. The backend refuses all of them at creation, and this screen is
 * where a person finds out weeks before the first firing.
 */
export function TriggerBoard() {
  const queryClient = useQueryClient();
  const triggers = useQuery({ queryKey: triggerKeys.all, queryFn: listTriggers });
  const skills = useQuery({ queryKey: skillKeys.all, queryFn: listSkills });
  const devices = useQuery({ queryKey: deviceKeys.all, queryFn: listDevices });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: triggerKeys.all });
  const complain = (error: unknown) =>
    toast.error(error instanceof ApiError ? error.message : "that did not work");

  const enable = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      setTriggerEnabled(id, enabled, enabled ? "" : "paused from the console"),
    onSuccess: (trigger) => {
      toast.success(trigger.enabled ? "scheduled" : "paused — nothing will fire");
      void invalidate();
    },
    onError: complain,
  });

  const fire = useMutation({
    mutationFn: fireTrigger,
    onSuccess: () => {
      toast.success("firing now, with the trigger's own values and authorisation");
      void invalidate();
    },
    onError: complain,
  });

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        {/* The route is Triggers and the glossary says a trigger is `manual`,
            `schedule` or `inbound` -- so naming the whole page after one of the
            three left the nav and the heading disagreeing about where you were.
            "On a clock" is the schedule section inside it. */}
        <h1 className="text-2xl font-semibold tracking-tight">Triggers</h1>
        <p className="text-muted-foreground max-w-2xl text-sm">
          A taught skill, a schedule, and the values it runs with. Nothing here
          fires until somebody stands behind it: a skill that changes a warehouse
          needs a name on every run it will ever start, and that name is the
          person who creates the trigger.
        </p>

        {triggers.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : triggers.data?.length ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Skill</TableHead>
                <TableHead>When</TableHead>
                <TableHead>Where</TableHead>
                <TableHead>Writes</TableHead>
                <TableHead>Last fired</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {triggers.data.map((trigger) => (
                <Row
                  key={trigger.id}
                  trigger={trigger}
                  onEnable={(enabled) => enable.mutate({ id: trigger.id, enabled })}
                  onFire={() => fire.mutate(trigger.id)}
                  busy={enable.isPending || fire.isPending}
                />
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="text-muted-foreground text-sm">
            Nothing runs on a clock yet.
          </p>
        )}
      </section>

      <NewTrigger
        skills={skills.data ?? []}
        devices={devices.data ?? []}
        onCreated={invalidate}
        onError={complain}
      />
    </div>
  );
}

function Row({
  trigger,
  onEnable,
  onFire,
  busy,
}: {
  trigger: TriggerModel;
  onEnable: (enabled: boolean) => void;
  onFire: () => void;
  busy: boolean;
}) {
  return (
    <TableRow>
      <TableCell>
        <Link className="underline" href={`/skills/${trigger.skill_id}`}>
          {trigger.skill_id}
        </Link>
        <p className="text-muted-foreground text-xs">
          {trigger.medium === "ui" ? "in a browser" : "as calls"}
          {trigger.device_id ? " · in the operator's own browser" : ""}
        </p>
      </TableCell>
      <TableCell>
        <code className="text-xs">{trigger.cron ?? trigger.kind}</code>
        <p className="text-muted-foreground text-xs">{trigger.timezone}</p>
      </TableCell>
      <TableCell>
        {/* Two different permissions, and a screen that blurred them would be a
            screen that granted the wrong one. */}
        {trigger.may_take_focus ? (
          <Badge variant="outline">may take the screen</Badge>
        ) : (
          <span className="text-muted-foreground text-xs">runs behind you</span>
        )}
      </TableCell>
      <TableCell>
        {trigger.writes ? (
          <span className="text-xs">
            {trigger.requires_confirmation ? "asks first" : "sends without asking"}
            <br />
            <span className="text-muted-foreground">
              {trigger.authorized_by ?? "nobody"} stands behind it
            </span>
          </span>
        ) : (
          <span className="text-muted-foreground text-xs">reads only</span>
        )}
      </TableCell>
      <TableCell className="text-xs">
        {trigger.last_fired_at ? new Date(trigger.last_fired_at).toLocaleString() : "never"}
        {trigger.disabled_reason ? (
          <p className="text-muted-foreground">{trigger.disabled_reason}</p>
        ) : null}
      </TableCell>
      <TableCell className="flex justify-end gap-2">
        <Button variant="outline" size="sm" disabled={busy} onClick={onFire}>
          Fire now
        </Button>
        <Button
          variant={trigger.enabled ? "outline" : "default"}
          size="sm"
          disabled={busy}
          onClick={() => onEnable(!trigger.enabled)}
        >
          {trigger.enabled ? "Pause" : "Resume"}
        </Button>
      </TableCell>
    </TableRow>
  );
}

function NewTrigger({
  skills,
  devices,
  onCreated,
  onError,
}: {
  skills: { id: string; name: string; systems?: string[] }[];
  devices: DeviceModel[];
  onCreated: () => void;
  onError: (error: unknown) => void;
}) {
  const [skillId, setSkillId] = useState("");
  const [repeat, setRepeat] = useState<Repeat>("weekdays");
  const [at, setAt] = useState("07:00");
  const [weekday, setWeekday] = useState(1);
  const [written, setWritten] = useState("0 7 * * 1-5");
  const cron = repeat === "custom" ? written : toCron(repeat, at, weekday);
  const inWords = cron ? describeCron(cron) : null;
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
  );
  const [deviceId, setDeviceId] = useState("");
  // A skill that touches two systems runs only in a browser signed in to both,
  // so a schedule with no browser named would refuse at every fire -- and a
  // schedule that never runs is worse than one that was never made.
  const crosses = (skills.find((skill) => skill.id === skillId)?.systems ?? []).length > 1;
  // Derived beside the disabled condition it explains, so the two cannot drift.
  const missing = [
    !skillId && "a skill",
    !cron && "a schedule",
    crosses && !deviceId && "a browser to run it in",
  ]
    .filter(Boolean)
    .join(", ");
  const [authorized, setAuthorized] = useState(false);
  const [autoApprove, setAutoApprove] = useState(false);
  const [mayTakeFocus, setMayTakeFocus] = useState(false);

  const create = useMutation({
    mutationFn: createTrigger,
    onSuccess: () => {
      toast.success("scheduled");
      setSkillId("");
      setDeviceId("");
      setAuthorized(false);
      setAutoApprove(false);
      setMayTakeFocus(false);
      onCreated();
    },
    onError,
  });

  return (
    <section className="flex max-w-2xl flex-col gap-4">
      <h2 className="text-lg font-semibold">Put a skill on a clock</h2>

      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!cron) return;
          create.mutate({
            skill_id: skillId,
            // Named rather than defaulted: the generated type has no defaults,
            // and a schedule that ran as a manual trigger would never fire.
            kind: "schedule",
            // A run in somebody's browser drives the interface; one on the
            // server replays the calls. Naming a device and asking for network
            // replay would be asking a laptop to do what needs no laptop.
            // A run in somebody's browser drives the interface; one on the
            // server replays the calls. A workflow is the exception on
            // purpose: its steps are calls, and what the browser is there for
            // is the session each system's tab already holds.
            medium: deviceId && !crosses ? "ui" : "network",
            device_id: deviceId || null,
            cron,
            timezone,
            authorized_by: authorized,
            auto_approve: autoApprove,
            may_take_focus: mayTakeFocus,
          });
        }}
      >
        <div className="flex flex-col gap-2">
          <Label htmlFor="skill">Skill</Label>
          <select
            id="skill"
            required
            className="border-input h-9 rounded-md border px-3 text-sm"
            value={skillId}
            onChange={(event) => setSkillId(event.target.value)}
          >
            <option value="">choose a taught skill</option>
            {skills.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex gap-4">
          <div className="flex flex-1 flex-col gap-2">
            <Label htmlFor="repeat">When</Label>
            <div className="flex gap-2">
              <select
                id="repeat"
                className="border-input h-9 flex-1 rounded-md border px-3 text-sm"
                value={repeat}
                onChange={(event) => setRepeat(event.target.value as Repeat)}
              >
                <option value="weekdays">Every weekday</option>
                <option value="daily">Every day</option>
                <option value="weekly">Every week on</option>
                <option value="custom">A cron expression</option>
              </select>
              {repeat === "weekly" ? (
                <select
                  aria-label="Day"
                  className="border-input h-9 rounded-md border px-3 text-sm"
                  value={weekday}
                  onChange={(event) => setWeekday(Number(event.target.value))}
                >
                  {["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    .map((day, index) => (
                      <option key={day} value={index}>
                        {day}
                      </option>
                    ))}
                </select>
              ) : null}
              {repeat === "custom" ? null : (
                <Input
                  aria-label="Time"
                  type="time"
                  className="w-32"
                  value={at}
                  onChange={(event) => setAt(event.target.value)}
                />
              )}
            </div>
            {repeat === "custom" ? (
              <Input
                aria-label="Cron expression"
                value={written}
                onChange={(event) => setWritten(event.target.value)}
              />
            ) : null}
            {/* What is actually about to be saved, in both languages. The
                expression because somebody will want to copy it, and the words
                because `0 7 * * 1-5` firing on Sundays is a typo nobody can
                see. */}
            <p className="text-muted-foreground text-xs">
              {cron ? (
                <>
                  <code>{cron}</code>
                  {" — "}
                  {inWords ?? "the scheduler will read this; I cannot put it in words"}
                </>
              ) : (
                "give it a time to run at"
              )}
            </p>
          </div>
          <div className="flex flex-1 flex-col gap-2">
            <Label htmlFor="timezone">Where</Label>
            <Input
              id="timezone"
              value={timezone}
              onChange={(event) => setTimezone(event.target.value)}
            />
            <p className="text-muted-foreground text-xs">
              The warehouse&apos;s, not the server&apos;s — so seven is seven in
              March and in November.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="device">Where it runs</Label>
          <select
            id="device"
            className="border-input h-9 rounded-md border px-3 text-sm"
            value={deviceId}
            onChange={(event) => {
              setDeviceId(event.target.value);
              // A schedule with no browser has no screen to take, and leaving
              // the box ticked would show a permission that reaches nothing.
              if (!event.target.value) setMayTakeFocus(false);
            }}
          >
            <option value="" disabled={crosses}>
              on the server, as calls
            </option>
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                in {device.label}&apos;s browser
              </option>
            ))}
          </select>
          <p className="text-muted-foreground text-xs">
            {crosses
              ? "This skill works across two systems, so it runs in a browser signed in to both — the server holds credentials for one of them at most."
              : "A run in somebody's own browser carries their session, and happens only while that browser is connected — a property of a laptop rather than a fault."}
          </p>
        </div>

        {/* Three separate permissions, deliberately three checkboxes. Each one
            is a different thing to regret at three in the morning, and a single
            "enable automation" switch would grant all three. */}
        <Permission
          id="authorized"
          checked={authorized}
          onChange={setAuthorized}
          label="I stand behind every run this starts"
          note="Required for a skill that changes the system. The name comes from your credential, and it is what the audit trail shows for a warehouse write nobody watched."
        />
        <Permission
          id="auto-approve"
          checked={autoApprove}
          onChange={setAutoApprove}
          label="Send the writes without asking"
          note="Every firing, unattended. Without this the run stops at the first write and waits for somebody — which is what you want until this skill has proved itself."
        />
        <Permission
          id="may-take-focus"
          checked={mayTakeFocus}
          onChange={setMayTakeFocus}
          disabled={!deviceId}
          label="May bring a tab to the front"
          note={
            deviceId
              ? "The operator asked for this and is watching. Without it the extension refuses a command that would move their tab, which is what you want for anything that fires while nobody is there."
              : "Only for a run in somebody's own browser — choose one above. A schedule that runs on the server has no screen to take."
          }
        />

        <div className="flex flex-col gap-2">
          {/* A disabled control that does not say what it is waiting for is a
              control people work around. Same rule as the promotion button on a
              skill: refuse on the page, not on the click. */}
          {missing && <p className="text-muted-foreground text-xs">Still needed: {missing}</p>}
          <Button
            type="submit"
            disabled={!skillId || !cron || create.isPending || (crosses && !deviceId)}
          >
            Schedule it
          </Button>
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
    <div className={`flex gap-3 ${disabled ? "opacity-60" : ""}`}>
      <input
        id={id}
        type="checkbox"
        className="mt-1"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <div>
        <Label htmlFor={id}>{label}</Label>
        <p className="text-muted-foreground text-xs">{note}</p>
      </div>
    </div>
  );
}
