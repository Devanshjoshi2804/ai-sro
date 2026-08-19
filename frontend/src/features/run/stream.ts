import { useEffect, useState } from "react";
import { credential } from "@/lib/api/credential";
import { env } from "@/lib/env";
import type { RunModel } from "@/features/run/api";

export type RunStep = RunModel["steps"][number];

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
  const [seen, setSeen] = useState<{ runId: string; steps: RunStep[]; run: RunModel | null }>({
    runId: "",
    steps: [],
    run: null,
  });
  const steps = seen.runId === runId ? seen.steps : [];
  const run = seen.runId === runId ? seen.run : null;

  useEffect(() => {
    if (!runId || !live) return;
    const controller = new AbortController();

    const land = (step: RunStep) =>
      setSeen((was) =>
        was.runId === runId
          ? { ...was, steps: [...was.steps, step] }
          : { runId, steps: [step], run: null },
      );
    const finish = (finished: RunModel) =>
      setSeen((was) => ({ runId, steps: was.runId === runId ? was.steps : [], run: finished }));

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
            const payload = JSON.parse(data) as RunStep & RunModel;
            if (kind === "step") land(payload as RunStep);
            if (kind === "done") finish(payload as RunModel);
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

  return { steps, run };
}
