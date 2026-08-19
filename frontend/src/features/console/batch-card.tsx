"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { runBatch, runKeys, type BatchItem, type BatchResult } from "@/features/run/api";
import { ApiError } from "@/lib/api/client";
import { ink, mono } from "@/features/console/theme";

/**
 * What was read from the sentence, before anything is sent.
 *
 * The table is the thing being confirmed, not the sentence. "Update these six
 * SKUs" is six writes, and the difference between the right six and a plausible
 * six is not visible in prose — so the values are shown as values, and pressing
 * the button is what authorises them.
 */
export function BatchCard({
  skillId,
  skillName,
  items,
  runnable,
}: {
  skillId: string;
  skillName: string;
  items: Record<string, string>[];
  runnable: boolean;
}) {
  const queryClient = useQueryClient();
  const [result, setResult] = useState<BatchResult | null>(null);

  const go = useMutation({
    // Confirming is what this click means. Who confirmed comes from the
    // credential on the request, not from anything this page can set.
    mutationFn: () => runBatch(skillId, items, { authorizedBy: "confirmed" }),
    onSuccess: (batch) => {
      setResult(batch);
      void queryClient.invalidateQueries({ queryKey: runKeys.all });
      if (batch.stopped_early) {
        toast.warning("The batch stopped early", { description: batch.stopped_early });
      }
    },
    onError: (error) =>
      toast.error("The batch did not start", {
        description: error instanceof ApiError ? error.problem.detail : String(error),
      }),
  });

  const columns = Array.from(new Set(items.flatMap((item) => Object.keys(item))));

  return (
    <div style={{ border: `1px solid ${ink.line}`, borderRadius: 12, background: ink.panel }}>
      <div
        style={{
          padding: "12px 16px",
          borderBottom: `1px solid ${ink.lineSoft}`,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span style={{ fontSize: 13.5, fontWeight: 700 }}>{skillName}</span>
        <span style={{ fontSize: 11.5, color: ink.textMuted }}>
          {items.length} item{items.length === 1 ? "" : "s"}
          {result ? ` · ${result.performed} applied` : " · nothing sent yet"}
        </span>
      </div>

      <div style={{ overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ textAlign: "left", color: ink.textMuted }}>
              {columns.map((name) => (
                <th key={name} style={cell}>
                  {name}
                </th>
              ))}
              <th style={cell}>status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr key={index}>
                {columns.map((name) => (
                  <td key={name} style={{ ...cell, fontFamily: mono }}>
                    {item[name] ?? "—"}
                  </td>
                ))}
                <td style={cell}>
                  <Status item={result?.items[index]} pending={go.isPending} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {result?.stopped_early && (
        <div style={{ padding: "10px 16px", fontSize: 12, color: ink.danger }}>
          {/* The rest were never attempted, which is the point of saying so. */}
          Stopped before the rest: {result.stopped_early}
        </div>
      )}

      {!result && (
        <div
          style={{
            padding: "11px 16px",
            borderTop: `1px solid ${ink.lineSoft}`,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <button
            onClick={() => go.mutate()}
            disabled={!runnable || go.isPending}
            title={runnable ? undefined : "Nobody has reviewed this skill yet"}
            style={{
              padding: "7px 14px",
              borderRadius: 8,
              border: "none",
              background: runnable ? ink.accent : "#E7E7E4",
              color: runnable ? "#fff" : ink.textMuted,
              fontSize: 12.5,
              fontWeight: 700,
              cursor: runnable ? "pointer" : "not-allowed",
            }}
          >
            {go.isPending ? "Running…" : `Run ${items.length}`}
          </button>
          <span style={{ fontSize: 11.5, color: ink.textSoft }}>
            Each item is its own run, verified on its own. Confirming this table is what the
            run records as its authorisation.
          </span>
        </div>
      )}
    </div>
  );
}

function Status({ item, pending }: { item?: BatchItem; pending: boolean }) {
  if (!item) {
    return <span style={{ color: ink.textMuted }}>{pending ? "…" : "waiting"}</span>;
  }
  const good = item.status === "succeeded";
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 7 }}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: good ? ink.good : ink.danger,
        }}
      />
      <span style={{ color: good ? ink.good : ink.danger }}>{item.status}</span>
      {item.run_id && (
        <Link href={`/runs/${item.run_id}`} style={{ color: ink.accentDeep, fontSize: 11 }}>
          run →
        </Link>
      )}
      {item.detail && (
        <span style={{ color: ink.textMuted, fontSize: 11 }}>{item.detail.slice(0, 70)}</span>
      )}
    </span>
  );
}

const cell = {
  padding: "8px 16px",
  borderBottom: `1px solid ${ink.lineSoft}`,
  whiteSpace: "nowrap",
} as const;
