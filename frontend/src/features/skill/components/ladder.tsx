import { Badge } from "@/components/ui/badge";
import type { TrackRecordModel } from "@/features/skill/api";

/**
 * The rungs, in the order autonomy is earned.
 *
 * Kept in one place because the lists disagreed: `skill-list.tsx` drew `shadow`
 * as a filled badge and `assisted` as a grey outline, so the *more* autonomous
 * rung looked like the quieter one, and the ladder that is the product's whole
 * trust argument read as decoration.
 */
const RUNGS = ["recorded", "shadow", "assisted", "autonomous"] as const;

/** How much of the ladder a version has climbed, as a rung and a position. */
export function Rung({ stage }: { stage: string }) {
  const reached = RUNGS.indexOf(stage as (typeof RUNGS)[number]);
  return (
    <span className="inline-flex items-center gap-2" title={`${stage} — rung ${reached + 1} of 4`}>
      <span aria-hidden className="flex gap-[3px]">
        {RUNGS.map((rung, index) => (
          <span
            key={rung}
            className={`h-[3px] w-3 rounded-full ${index <= reached ? "bg-brand" : "bg-border"}`}
          />
        ))}
      </span>
      <Badge variant="outline" className="font-mono text-[10px] tracking-wide uppercase">
        {stage}
      </Badge>
    </span>
  );
}

/**
 * The streak, and the distance to losing it.
 *
 * This was one sentence of six numbers — "0 clean in a row · 2 clean · 0 needed
 * a slower rung · 2 failed · 0 never reached the system" — for the mechanism the
 * entire product rests on. A streak is only worth reading beside the thing that
 * would break it, so the failures are drawn against their own limit rather than
 * listed as a tally.
 *
 * Both denominators come from the backend. A hardcoded 10 here would keep
 * saying 10 the day the domain changed its mind.
 */
export function Streak({
  record,
  refusal,
  demotion,
}: {
  record: TrackRecordModel;
  refusal: string | null;
  demotion: string | null;
}) {
  const needed = record.clean_runs_needed;
  const done = Math.min(record.clean_streak, needed);
  const left = record.failures_before_demotion - record.consecutive_failures;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <div
          role="meter"
          aria-valuenow={record.clean_streak}
          aria-valuemin={0}
          aria-valuemax={needed}
          aria-label="Clean runs in a row toward unattended"
          className="flex gap-1"
        >
          {Array.from({ length: needed }, (_, index) => (
            <span
              key={index}
              className={`h-1.5 flex-1 rounded-full ${index < done ? "bg-good" : "bg-border"}`}
            />
          ))}
        </div>
        <p className="text-muted-foreground text-xs tabular-nums">
          <span className="text-foreground font-medium">
            {record.clean_streak} of {needed}
          </span>{" "}
          clean runs in a row
          {refusal === null && " — this version has earned the right to run unattended"}
        </p>
      </div>

      {/* Only where there is something to lose. Drawing "3 failures away" under
          a version that has never run says nothing and reads as a warning. */}
      {record.consecutive_failures > 0 && (
        <p className="text-warn text-xs tabular-nums">
          {record.consecutive_failures} {record.consecutive_failures === 1 ? "failure" : "failures"}{" "}
          in a row.{" "}
          {left <= 0
            ? "The next one demotes it."
            : `${left} more ${left === 1 ? "demotes" : "would demote"} it.`}
        </p>
      )}

      {refusal && <p className="text-muted-foreground text-xs">Not yet: {refusal}</p>}
      {demotion && <p className="text-destructive text-xs">Demoted automatically: {demotion}</p>}

      <dl className="text-muted-foreground grid grid-cols-2 gap-x-6 gap-y-1 text-xs sm:grid-cols-4">
        <Tally label="clean" value={record.clean_runs} />
        <Tally label="needed a slower rung" value={record.degraded_runs} />
        <Tally label="failed" value={record.failed_runs} />
        {/* Its own number on purpose: a week of closed laptops is not a week of
            a broken skill. */}
        <Tally label="never reached the system" value={record.unreachable_runs} />
      </dl>
    </div>
  );
}

function Tally({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="sr-only">{label}</dt>
      <dd className="text-foreground font-mono tabular-nums">{value}</dd>
      <span aria-hidden>{label}</span>
    </div>
  );
}
