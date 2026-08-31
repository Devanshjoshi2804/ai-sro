"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The furniture every list on this product needs and none of them had.
 *
 * Loading, error and empty were written three different ways and one of them
 * was a sentence in a table cell. Search was written nowhere, which is why
 * Recordings shows ten rows reading "Create a work area · bf56-kms… · SG" and
 * offers no way to tell them apart or find the two you meant to pair.
 *
 * What it deliberately does not do: sorting, density, saved views, pagination.
 * Nothing has asked for them, the tables are short, and a filter nobody uses is
 * a filter somebody has to keep working.
 */
export function DataView<Row>({
  title,
  description,
  actions,
  loading,
  error,
  rows,
  matches,
  facet,
  empty,
  children,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  loading: boolean;
  error: unknown;
  rows: Row[];
  /** Omit to hide the search box: a list of four things does not need one. */
  matches?: (row: Row, term: string) => boolean;
  /** Chips built from the values actually present, so a status nothing has is
   * never offered and a new one never has to be registered here. */
  facet?: { name: string; of: (row: Row) => string | null | undefined };
  empty: { line: string; hint?: ReactNode };
  children: (shown: Row[]) => ReactNode;
}) {
  const [term, setTerm] = useState("");
  const [only, setOnly] = useState<string | null>(null);

  const values = useMemo(() => {
    if (!facet) return [];
    const seen = new Map<string, number>();
    for (const row of rows) {
      const value = facet.of(row);
      if (value) seen.set(value, (seen.get(value) ?? 0) + 1);
    }
    return [...seen.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows, facet]);

  const shown = useMemo(() => {
    const cleaned = term.trim().toLowerCase();
    return rows.filter((row) => {
      if (only && facet && facet.of(row) !== only) return false;
      if (!cleaned || !matches) return true;
      return matches(row, cleaned);
    });
  }, [rows, term, only, matches, facet]);

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="flex items-baseline gap-2 text-2xl font-semibold tracking-tight">
            {title}
            {!loading && !error && (
              <span className="text-muted-foreground font-mono text-sm tabular-nums">
                {shown.length === rows.length ? rows.length : `${shown.length} of ${rows.length}`}
              </span>
            )}
          </h1>
          {description && <p className="text-muted-foreground text-sm">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </header>

      {!loading && !error && rows.length > 0 && (matches || values.length > 1) && (
        <div className="flex flex-wrap items-center gap-2">
          {matches && (
            <Input
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              placeholder={`Search ${title.toLowerCase()}`}
              aria-label={`Search ${title.toLowerCase()}`}
              className="max-w-xs"
            />
          )}
          {/* More than one value, or it is a filter with one setting. */}
          {values.length > 1 &&
            values.map(([value, count]) => (
              <button
                key={value}
                type="button"
                aria-pressed={only === value}
                onClick={() => setOnly(only === value ? null : value)}
                className="cursor-pointer"
              >
                <Badge
                  variant={only === value ? "secondary" : "outline"}
                  className={only === value ? "border-ring" : "text-muted-foreground"}
                >
                  {value} <span className="ml-1 font-mono tabular-nums">{count}</span>
                </Badge>
              </button>
            ))}
        </div>
      )}

      {loading ? (
        <Skeleton className="h-64 w-full" />
      ) : error ? (
        /* Said, rather than an empty table. A list that renders nothing on a
           failed request makes the claim "there are none of these", which is a
           different and much worse thing to tell somebody. */
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-6">
          <p className="text-destructive text-sm font-medium">This could not be read.</p>
          <p className="text-muted-foreground mt-1 font-mono text-xs">{String(error)}</p>
        </div>
      ) : rows.length === 0 ? (
        <Nothing line={empty.line} hint={empty.hint} />
      ) : shown.length === 0 ? (
        <Nothing
          line="Nothing here matches that."
          hint={
            <button
              type="button"
              className="text-brand underline"
              onClick={() => {
                setTerm("");
                setOnly(null);
              }}
            >
              Clear the search and filters
            </button>
          }
        />
      ) : (
        children(shown)
      )}
    </div>
  );
}

/** An empty state with somewhere to go, rather than a sentence in a table cell. */
function Nothing({ line, hint }: { line: string; hint?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed px-6 py-14 text-center">
      <p className="text-sm font-medium">{line}</p>
      {hint && <div className="text-muted-foreground max-w-md text-sm">{hint}</div>}
    </div>
  );
}
