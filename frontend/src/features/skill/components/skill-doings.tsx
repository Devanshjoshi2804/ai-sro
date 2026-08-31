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
  differs,
  readingOf,
  shapesOf,
  spanOf,
  type Shape,
} from "@/features/skill/components/doings-shape";
import {
  getDoings,
  skillKeys,
  type Demonstration,
  type ParameterModel,
  type SkillVersionModel,
} from "@/features/skill/api";

/**
 * Every way this task has been demonstrated, side by side.
 *
 * A column is a *shape* — which fields somebody filled and which they left out
 * — not a single doing. Ten demonstrations of one job are usually three or
 * four ways of doing it, and ten near-identical columns bury the one that is
 * different. Values differing between doings is expected; it is what makes a
 * field a parameter. Which fields were filled at all is the fact worth a
 * column of its own.
 *
 * Three states per cell, and they are three different facts:
 *
 * - a value — these doings put that there
 * - *left empty* — sent holding nothing, which is the evidence behind every
 *   optional field
 * - *not recorded* — these doings do not answer for that field, because the
 *   calls they made do not fit the one this version sends
 *
 * The third is the one that matters most. Collapsing it into either of the
 * others would put a value in a table of measurements that nobody measured.
 */
const OPEN_AT_FIRST = 4;

export function SkillDoings({ skillId, version }: { skillId: string; version: SkillVersionModel }) {
  const [showAll, setShowAll] = useState(false);
  const [showAgreed, setShowAgreed] = useState(false);
  const [ungrouped, setUngrouped] = useState(false);

  const doings = useQuery({
    queryKey: skillKeys.doings(skillId, version.version),
    queryFn: () => getDoings(skillId, version.version),
    staleTime: Infinity,
  });

  const all = doings.data ?? [];
  const names = version.parameters.map((parameter) => parameter.name);
  const grouped = shapesOf(all, names);
  // Ungrouped is the same table with every shape holding one doing: one code
  // path, so the two views cannot drift into disagreeing about the evidence.
  const shapes = ungrouped
    ? all.map((doing) => ({ key: doing.recording_id, doings: [doing] }))
    : grouped;
  const shown = showAll ? shapes : shapes.slice(0, OPEN_AT_FIRST);

  // Pictures are fetched only for the columns on screen: a skill demonstrated
  // fifty times would otherwise mint fifty sets of presigned links to render
  // four of them.
  const leaders = shown.map((shape) => shape.doings[0]);
  const media = useQueries({
    queries: leaders.map((doing: Demonstration) => ({
      queryKey: [...recordingKeys.detail(doing.recording_id), "media"],
      queryFn: () => getMedia(doing.recording_id),
    })),
  });
  const frames = useQueries({
    queries: leaders.map((doing: Demonstration) => ({
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
          None of the demonstrations this version cites can be read back — they have aged out
          of retention. The version still names them, which is why this says so rather than
          showing nothing.
        </p>
      </section>
    );
  }

  const shots = media.map((one) => shotsByFrame(one.data));
  const conditional = version.steps.filter((step) => step.when !== null);

  // Judged across every doing, not only the columns on screen: a field two
  // hidden doings disagree about is a field that differs, and hiding the row
  // because the visible columns happen to match would be the screen lying
  // about its own evidence.
  const varying = version.parameters.filter((parameter) => differs(all, parameter.name));
  const agreed = version.parameters.filter((parameter) => !differs(all, parameter.name));
  const rows = showAgreed ? [...varying, ...agreed] : varying;
  const hiddenColumns = shapes.length - shown.length;

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
          {grouped.length < all.length && (
            <Button variant="ghost" size="sm" onClick={() => setUngrouped(!ungrouped)}>
              {ungrouped ? "Group by shape" : "Show every doing"}
            </Button>
          )}
          {shapes.length > OPEN_AT_FIRST && (
            <Button variant="ghost" size="sm" onClick={() => setShowAll(!showAll)}>
              {showAll ? `Show ${OPEN_AT_FIRST}` : `Show all ${shapes.length}`}
            </Button>
          )}
        </div>
      </header>

      <p className="text-muted-foreground text-sm">
        {ungrouped
          ? "One column per demonstration."
          : `${grouped.length} distinct ${
              grouped.length === 1 ? "way" : "ways"
            } this task has been done — doings that filled the same fields share a column, whatever they typed.`}{" "}
        Only the fields the doings disagree on are shown; that disagreement is what made each
        one a parameter rather than a fixed value.
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
              {shown.map((shape) => (
                <th key={shape.key} className="min-w-44 px-4 py-2 text-left font-medium">
                  <ShapeHeader shape={shape} />
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
                    <Field parameter={parameter} />
                  </td>
                  {shown.map((shape) => (
                    <Cell key={shape.key} shape={shape} name={parameter.name} />
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
              {shown.map((shape, column) => {
                const first = frames[column]?.data?.frames[0];
                return (
                  <td key={shape.key} className="px-4 py-2 align-top">
                    {first ? (
                      <FrameShot
                        shot={shots[column]?.get(first.index)}
                        label={`${shape.doings[0].recording_id} · #${first.index} ${first.action_kind}`}
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

      {hiddenColumns > 0 && (
        <p className="text-muted-foreground text-xs">
          {hiddenColumns} more {hiddenColumns === 1 ? "column is" : "columns are"} kept and not
          shown.
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

function Field({ parameter }: { parameter: ParameterModel }) {
  return (
    <>
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
          left out, some doing sent <code className="font-mono">{parameter.absent_as}</code>
        </p>
      )}
    </>
  );
}

/** How many doings share this shape, when they happened, and who did them. */
function ShapeHeader({ shape }: { shape: Shape }) {
  const [open, setOpen] = useState(false);
  const many = shape.doings.length > 1;
  const people = [...new Set(shape.doings.map((doing) => doing.demonstrator))];

  return (
    <div className="space-y-1">
      <span className="flex items-center gap-2">
        {many ? `${shape.doings.length} doings` : "1 doing"}
        {shape.doings.some((doing) => doing.diffed) && (
          <Badge variant="secondary" className="text-xs font-normal">
            diffed
          </Badge>
        )}
      </span>
      <span className="text-muted-foreground block text-xs font-normal">
        {spanOf(shape)} · {people.join(", ")}
      </span>
      {many ? (
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="text-muted-foreground text-xs font-normal underline"
        >
          {open ? "hide" : "which ones"}
        </button>
      ) : (
        <Link
          href={`/recordings/${shape.doings[0].recording_id}`}
          className="text-muted-foreground block text-xs font-normal underline"
        >
          open
        </Link>
      )}
      {open && (
        <ul className="space-y-0.5">
          {shape.doings.map((doing) => (
            <li key={doing.recording_id}>
              <Link
                href={`/recordings/${doing.recording_id}`}
                className="text-muted-foreground text-xs font-normal hover:underline"
              >
                {new Date(doing.started_at).toLocaleDateString()} · {doing.frames} steps
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Cell({ shape, name }: { shape: Shape; name: string }) {
  const [open, setOpen] = useState(false);
  const reading = readingOf(shape, name);

  if (reading.fill === "unread") {
    return (
      <td className="px-4 py-2 align-top">
        <span className="text-muted-foreground/60 text-xs italic">not recorded</span>
      </td>
    );
  }
  if (reading.fill === "empty") {
    return (
      <td className="px-4 py-2 align-top">
        <span className="text-muted-foreground italic">left empty</span>
      </td>
    );
  }

  const [first, ...rest] = reading.values;
  return (
    <td className="px-4 py-2 align-top">
      <span className="font-mono text-xs break-all">{first}</span>
      {rest.length > 0 &&
        (open ? (
          <ul className="mt-1 space-y-0.5">
            {rest.map((value) => (
              <li key={value} className="font-mono text-xs break-all">
                {value}
              </li>
            ))}
          </ul>
        ) : (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="text-muted-foreground ml-2 text-xs underline"
          >
            +{rest.length}
          </button>
        ))}
    </td>
  );
}
