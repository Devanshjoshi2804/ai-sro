import { useEffect, useState } from "react";
import { credential } from "@/lib/api/credential";
import { env } from "@/lib/env";
import type { RunModel } from "@/features/run/api";

export type RunStep = RunModel["steps"][number];

/**
 * The browser this run is driving has asked to be left alone.
 *
 * Not part of the run row: it lives for a few seconds in the process holding
 * the socket, so the stream is the only place it exists. `heldMs` is what the
 * backend will actually honour rather than what the browser asked for, so a
 * countdown drawn from it does not promise a wait nobody intends to take.
 */
export type Waiting = { index: number; heldMs: number | null };

/**
 * A run as it happens, rather than when it is over.
 *
 * `fetch` rather than `EventSource`: the credential travels in a header, and
 * EventSource cannot send one — putting a token in the query string would put
 * it in every proxy log between here and the warehouse.
 *
 * The stream is derived from the run row, so a browser that connects late or
 * reconnects gets every step so far rather than only what it was awake for.
 */
export function useRunStream(runId: string | null | undefined, live: boolean) {
  // Keyed by run: a new run starts from nothing without an effect having to
  // clear the last one's steps, which is a cascading render and reads as a
  // flash of the previous run in the card.
  const [seen, setSeen] = useState<{
    runId: string;
    steps: RunStep[];
    run: RunModel | null;
    waiting: Waiting | null;
  }>({ runId: "", steps: [], run: null, waiting: null });
  const steps = seen.runId === runId ? seen.steps : [];
  const run = seen.runId === runId ? seen.run : null;
  const waiting = seen.runId === runId ? seen.waiting : null;

  useEffect(() => {
    if (!runId || !live) return;
    const controller = new AbortController();

    const land = (step: RunStep) =>
      setSeen((was) =>
        was.runId === runId
          ? { ...was, steps: [...was.steps, step] }
          : { runId, steps: [step], run: null, waiting: null },
      );
    const finish = (finished: RunModel) =>
      setSeen((was) => ({
        runId,
        steps: was.runId === runId ? was.steps : [],
        run: finished,
        // A finished run is not waiting for anybody.
        waiting: null,
      }));
    const hold = (next: Waiting | null) =>
      setSeen((was) =>
        was.runId === runId
          ? { ...was, waiting: next }
          : { runId, steps: [], run: null, waiting: next },
      );

    void (async () => {
      try {
        const response = await fetch(`${env.NEXT_PUBLIC_API_URL}/v1/runs/${runId}/stream`, {
          headers: { Authorization: `Bearer ${credential() ?? ""}` },
          signal: controller.signal,
        });
        const body = response.body;
        if (!body) return;

        const reader = body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += value;
          // Events are separated by a blank line; a chunk can split one in
          // half, so what is left over stays in the buffer.
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() ?? "";
          for (const chunk of chunks) {
            const kind = /^event: (.+)$/m.exec(chunk)?.[1];
            const data = /^data: (.+)$/m.exec(chunk)?.[1];
            if (!kind || !data) continue;
            const payload = JSON.parse(data) as RunStep &
              RunModel & { index: number; held_ms: number | null };
            if (kind === "step") land(payload as RunStep);
            if (kind === "done") finish(payload as RunModel);
            // Sent only when it changes, so `held_ms: null` is the event that
            // says the operator stopped typing rather than an empty one.
            if (kind === "waiting") {
              hold(
                payload.held_ms === null
                  ? null
                  : { index: payload.index, heldMs: payload.held_ms },
              );
            }
            // The run is not ours or never existed. Nothing to watch, and
            // holding the connection open would be a browser tab waiting on a
            // row that is never coming.
            if (kind === "gone") return;
          }
        }
      } catch {
        // Aborted on unmount, or the connection dropped. The card falls back
        // to fetching the run, which is the same truth a moment later.
      }
    })();

    return () => controller.abort();
  }, [runId, live]);

  return { steps, run, waiting };
}
