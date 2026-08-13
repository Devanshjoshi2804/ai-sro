"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * The console transcript.
 *
 * Deliberately client-side and deliberately thin: every entry records something
 * that actually happened against the backend — a session opened, a run sealed,
 * a skill induced — and holds the id to prove it. There is no thread backend
 * yet (that is Phase 4), so a reload starts a new transcript, and the entries
 * that matter can always be reconstructed from recordings and skills.
 *
 * What it must never do is invent an entry. If a step did not happen against
 * the API, it does not appear here.
 */
export type Entry =
  | { kind: "operator"; id: string; text: string }
  | { kind: "system"; id: string; text: string }
  | { kind: "session"; id: string; recordingId: string; run: number; label: string }
  | { kind: "sealed"; id: string; recordingId: string; run: number; frames: number }
  | { kind: "skill"; id: string; skillId: string; version: number };

/**
 * `Omit` over a union collapses it to the keys every member shares, which would
 * leave `add` accepting only `kind`. Distributing keeps each variant intact.
 */
type NewEntry = Entry extends infer Variant
  ? Variant extends { id: string }
    ? Omit<Variant, "id">
    : never
  : never;

type ThreadState = {
  entries: Entry[];
  add: (entry: NewEntry) => void;
  reset: () => void;
  /** Recordings sealed in this transcript, oldest first — the induction pair. */
  sealedRecordings: string[];
};

const ThreadContext = createContext<ThreadState | null>(null);

let counter = 0;
const nextId = () => `e${++counter}`;

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<Entry[]>([]);

  const value = useMemo<ThreadState>(
    () => ({
      entries,
      add: (entry) => setEntries((current) => [...current, { ...entry, id: nextId() } as Entry]),
      reset: () => setEntries([]),
      sealedRecordings: entries
        .filter((entry): entry is Extract<Entry, { kind: "sealed" }> => entry.kind === "sealed")
        .map((entry) => entry.recordingId),
    }),
    [entries],
  );

  return <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>;
}

export function useThread() {
  const context = useContext(ThreadContext);
  if (!context) throw new Error("useThread must be used inside a ThreadProvider");
  return context;
}
