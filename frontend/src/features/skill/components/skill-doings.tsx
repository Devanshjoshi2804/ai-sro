"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getMedia, getRecording, recordingKeys } from "@/features/recording/api";
import { FrameShot, shotsByFrame } from "@/features/recording/components/frame-shot";
import {
  getDoings,
  skillKeys,
  type Demonstration,
  type SkillVersionModel,
} from "@/features/skill/api";

/**
 * Every doing this version was learned from, side by side.
 *
 * A task demonstrated ten times is kept ten times, and until now nine of those
 * were thrown away at render time. What differs between the columns is not
 * trivia — it is the reason each parameter is a parameter, and the reason an
 * optional field is optional.
 *
 * Three states per cell, and they are three different facts:
 *
 * - a value — this doing put that there
 * - *left empty* — this doing sent the field holding nothing, which is the
 *   evidence behind every optional field
 * - *not recorded* — this doing does not answer for that field at all, because
 *   the call it made does not fit the one this version sends
 *
 * The third is the one that matters most. Collapsing it into either of the
 * others would put a value in a table of measurements that nobody measured.
 */
const OPEN_AT_FIRST = 3;

export function SkillDoings({ skillId, version }: { skillId: string; version: SkillVersionModel }) {
  const [showAll, setShowAll] = useState(false);
  const [showAgreed, setShowAgreed] = useState(false);

  const doings = useQuery({
    queryKey: skillKeys.doings(skillId, version.version),
    queryFn: () => getDoings(skillId, version.version),
    staleTime: Infinity,
  });

  const all = doings.data ?? [];
  const shown = showAll ? all : all.slice(0, OPEN_AT_FIRST);

  // Pictures are fetched only for the columns on screen: a skill demonstrated
  // fifty times would otherwise mint fifty sets of presigned links to render
  // three of them.
  const media = useQueries({
    queries: shown.map((doing: Demonstration) => ({
      queryKey: [...recordingKeys.detail(doing.recording_id), "media"],
      queryFn: () => getMedia(doing.recording_id),
    })),
  });
  const firstFrames = useQueries({
    queries: shown.map((doing: Demonstration) => ({
      queryKey: recordingKeys.detail(doing.recording_id),
      queryFn: () => getRecording(doing.recording_id),
      staleTime: Infinity,
    })),
  });

  if (doings.isLoading) return <Skeleton className="h-64 w-full" />;

  // Said out loud rather than rendered as nothing. A section that disappears
  // when its request fails is indistinguishable from a version that has no
  // demonstrations, and the reviewer has no way to tell that the evidence is
  // there and the screen simply could not reach it.
  if (doings.error) {
    return (
      <section className="space-y-2">
        <h2 className="text-lg font-medium">Doings</h2>
        <p className="text-destructive text-sm">
          The demonstrations behind this version could not be read: {String(doings.error)}
        </p>
      </section>
    );
  }
  if (all.length === 0) {
    return (
      <section className="space-y-2">
        <h2 className="text-lg font-medium">Doings</h2>
        <p className="text-muted-foreground text-sm">
          None of the demonstrations this version cites can be read back — they have aged out of
          retention. The version still names them, which is why this says so rather than showing
          nothing.
        </p>
      </section>
    );
  }

  const shots = media.map((one) => shotsByFrame(one.data));
  const conditional = version.steps.filter((step) => step.when !== null);
  const hidden = all.length - shown.length;

  // Judged across every doing, not only the columns on screen: a field two
  // hidden doings disagree about is a field that differs, and hiding the row
  // because the visible three happen to match would be the screen lying about
  // its own evidence.
  const varying = version.parameters.filter((parameter) => differs(all, parameter.name));
  const agreed = version.parameters.filter((parameter) => !differs(all, parameter.name));
  const rows = showAgreed ? [...varying, ...agreed] : varying;

  return (
    <section className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">
          Doings <span className="text-muted-foreground">({all.length})</span>
        </h2>
        <div className="flex items-center gap-2">
          {agreed.length > 0 && (
            <Button variant="ghost" size="sm" onClick={() => setShowAgreed(!showAgreed)}>
              {showAgreed
                ? "Only what differs"
                : `Show ${agreed.length} that ${agreed.length === 1 ? "agrees" : "agree"}`}
            </Button>
          )}
          {all.length > OPEN_AT_FIRST && (
            <Button variant="ghost" size="sm" onClick={() => setShowAll(!showAll)}>
              {showAll ? `Show ${OPEN_AT_FIRST}` : `Show all ${all.length}`}
            </Button>
          )}
        </div>
      </header>

      <p className="text-muted-foreground text-sm">
        Every demonstration this version was learned from. Only the fields the doings disagree on
        are shown — that disagreement is what made each one a parameter rather than a fixed value.
        {agreed.length > 0 && !showAgreed && (
          <>
            {" "}
            {agreed.length} {agreed.length === 1 ? "field is" : "fields are"} the same in every
            doing and hidden.
          </>
        )}
      </p>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-max border-collapse text-sm">
          <thead>
            <tr className="bg-muted/50 border-b">
              <th className="sticky left-0 z-10 w-56 bg-inherit px-4 py-2 text-left font-medium">
                Field
              </th>
              {shown.map((doing, column) => (
                <th key={doing.recording_id} className="min-w-44 px-4 py-2 text-left font-medium">
                  <Link
                    href={`/recordings/${doing.recording_id}`}
                    className="block hover:underline"
                  >
                    <span className="flex items-center gap-2">
                      doing {column + 1}
                      {doing.diffed && (
                        <Badge variant="secondary" className="text-xs font-normal">
                          diffed
                        </Badge>
                      )}
                    </span>
                    <span className="text-muted-foreground block text-xs font-normal">
                      {new Date(doing.started_at).toLocaleDateString()} · {doing.demonstrator} ·{" "}
                      {doing.frames} steps
                    </span>
                  </Link>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((parameter) => {
              const varies = differs(all, parameter.name);
              return (
                <tr
                  key={parameter.name}
                  className={`border-b last:border-0 ${varies ? "" : "text-muted-foreground"}`}
                >
                  <td
                    className={`sticky left-0 z-10 bg-inherit px-4 py-2 align-top ${
                      varies ? "border-l-2 border-amber-400" : ""
                    }`}
                  >
                    <code className="font-mono">${parameter.name}</code>
                    <span className="mt-1 flex flex-wrap items-center gap-1">
                      {parameter.optional && (
                        <Badge variant="outline" className="text-xs">
                          optional
                        </Badge>
                      )}
                      {parameter.evidence !== "proven" && (
                        <Badge variant="secondary" className="text-xs">
                          {parameter.evidence}
                        </Badge>
                      )}
                    </span>
                    {parameter.optional && parameter.absent_as && (
                      <p className="text-muted-foreground mt-1 text-xs">
                        left out, some doing sent{" "}
                        <code className="font-mono">{parameter.absent_as}</code>
                      </p>
                    )}
                  </td>
                  {shown.map((doing) => (
                    <Cell key={doing.recording_id} doing={doing} name={parameter.name} />
                  ))}
                </tr>
              );
            })}

            {rows.length === 0 && (
              <tr>
                <td colSpan={shown.length + 1} className="text-muted-foreground px-4 py-6">
                  {version.parameters.length === 0
                    ? "Nothing varied between these, so every value is fixed as demonstrated."
                    : "Every doing agrees on every field."}
                </td>
              </tr>
            )}

            <tr className="bg-muted/30 border-t">
              <td className="text-muted-foreground sticky left-0 z-10 bg-inherit px-4 py-2 align-top text-xs">
                What was on screen
              </td>
              {shown.map((doing, column) => {
                const first = firstFrames[column]?.data?.frames[0];
                return (
                  <td key={doing.recording_id} className="px-4 py-2 align-top">
                    {first ? (
                      <FrameShot
                        shot={shots[column]?.get(first.index)}
                        label={`doing ${column + 1} · #${first.index} ${first.action_kind}`}
                      />
                    ) : (
                      <span className="text-muted-foreground text-xs">no picture</span>
                    )}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      {hidden > 0 && (
        <p className="text-muted-foreground text-xs">
          {hidden} more {hidden === 1 ? "doing is" : "doings are"} kept and not shown.
        </p>
      )}

      {conditional.length > 0 && (
        <div className="rounded-md border px-4 py-3 text-sm">
          <p className="font-medium">Steps that did not happen every time</p>
          {conditional.map((step) => (
            <p key={step.index} className="text-muted-foreground mt-1 text-xs">
              <span className="tabular-nums">step {step.index}</span> · {step.intent} — only when{" "}
              <code className="font-mono">{step.when}</code>
            </p>
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * One doing's answer for one field, as something comparable.
 *
 * "Left empty" is its own reading rather than a missing one: a field every
 * doing left empty agrees, and a field one doing left empty while the others
 * filled it does not — which is exactly the row that makes a field optional.
 * The sentinel cannot collide with a value because no JSON body carries a NUL.
 */
function reading(doing: Demonstration, name: string): string {
  return doing.values[name] ?? "\u0000empty";
}

/**
 * Whether the doings disagree here — which is what made this a parameter.
 *
 * Only the doings that answer for the field are compared. A doing whose calls
 * do not fit what this version sends is silent, not dissenting, and counting
 * its silence as disagreement would mark every row the moment one
 * demonstration became unreadable.
 *
 * Fewer than two answers is not agreement either: with nothing to compare, the
 * row is shown rather than hidden behind a claim the evidence does not make.
 */
function differs(doings: Demonstration[], name: string): boolean {
  const answers = doings
    .filter((doing) => name in doing.values)
    .map((doing) => reading(doing, name));
  if (answers.length < 2) return true;
  return answers.some((answer) => answer !== answers[0]);
}

function Cell({ doing, name }: { doing: Demonstration; name: string }) {
  if (!(name in doing.values)) {
    return (
      <td className="px-4 py-2 align-top">
        <span className="text-muted-foreground/60 text-xs italic">not recorded</span>
      </td>
    );
  }
  const value = doing.values[name];
  return (
    <td className="px-4 py-2 align-top">
      {value === null ? (
        <span className="text-muted-foreground italic">left empty</span>
      ) : (
        <span className="font-mono text-xs break-all">{value}</span>
      )}
    </td>
  );
}
