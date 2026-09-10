"use client";

import { Badge } from "@/components/ui/badge";
import { useAwaitingCount } from "@/features/workflow/components/needs-a-person";

/**
 * How many runs are parked, in the bar, on whichever page you happen to be on.
 *
 * The rig put this on every view as an orange-bordered strip that collapsed to
 * nothing when nothing was waiting (`#needs:empty { display: none }`). Five
 * separate pages lose that, and a parked run is not an item in a queue: it is a
 * live Chrome holding a warehouse write open until somebody answers it. So the
 * count follows the operator around instead of waiting on `/needs` to be
 * visited.
 *
 * Nothing at zero, deliberately — a permanent `0` beside a nav link is chrome,
 * and chrome is what people stop seeing. The count is only ever an alarm.
 *
 * The layout that mounts this is a server component, which is the whole reason
 * this is its own file: `useAwaitingCount` is a hook.
 */
export function AwaitingBadge() {
  const count = useAwaitingCount();
  if (count === 0) return null;
  return (
    <Badge variant="destructive" className="ml-2">
      {count}
    </Badge>
  );
}
