"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { connectionKeys, openBrowsers } from "@/features/console/connect-panel";
import { LiveScreen } from "@/features/console/live-screen";
import { ink } from "@/features/console/theme";

/**
 * A strip that appears whenever this system is driving a browser.
 *
 * It signs itself in, replays screens and pursues goals in a window the
 * operator never sees, so a slow login and a stuck one look identical. This
 * says one is open and shows its screen on demand, so somebody can watch the
 * thing happen instead of waiting on a spinner.
 */
export function Watching() {
  const browsers = useQuery({
    queryKey: connectionKeys.browsers,
    queryFn: openBrowsers,
    // Often enough to catch a login that takes fifteen seconds; cheap because
    // it asks the provider, not the warehouse.
    refetchInterval: 4000,
  });

  const open = browsers.data ?? [];
  if (open.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {open.map((browser) => (
        <Browser key={browser.session_id} sessionId={browser.session_id} />
      ))}
    </div>
  );
}

/** One open browser, with its own screen a click away. */
function Browser({ sessionId }: { sessionId: string }) {
  const [watching, setWatching] = useState(false);

  return (
    <div
      style={{
        border: `1px solid ${ink.line}`,
        borderRadius: 8,
        background: ink.accentWash,
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 10px" }}>
        <Pulse />
        <span style={{ fontSize: 12, fontWeight: 600 }}>A browser is open</span>
        <span style={{ flex: 1 }} />
        <button
          type="button"
          onClick={() => setWatching((open) => !open)}
          style={{
            fontSize: 11.5,
            fontWeight: 700,
            color: ink.accentDeep,
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          {watching ? "Hide it" : "Watch it \u2192"}
        </button>
      </div>
      {/* Frames come from the session itself, so there is nothing to say about
          whether the provider has a viewer for it -- either it is painting or
          it has ended, and the screen says which. */}
      {watching && (
        <div style={{ padding: "0 10px 10px" }}>
          <LiveScreen sessionId={sessionId} />
        </div>
      )}
    </div>
  );
}

function Pulse() {
  return (
    <span
      style={{
        width: 7,
        height: 7,
        borderRadius: 999,
        background: ink.accent,
        boxShadow: `0 0 0 3px ${ink.accentWash}`,
      }}
    />
  );
}
