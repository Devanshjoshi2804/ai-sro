"use client";

import { useQuery } from "@tanstack/react-query";
import { readSpend, spendKeys } from "@/features/workflow/api";
import { spendLine } from "@/features/workflow/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** One query key, so the bar and the page can never disagree about the bill. */
function useSpend() {
  return useQuery({ queryKey: spendKeys.all, queryFn: readSpend, refetchInterval: 3000 });
}

/** The header line. Renders nothing rather than a number it cannot stand behind. */
export function SpendLine() {
  const spend = useSpend();
  if (!spend.data) return null;
  const { text, overCap } = spendLine(spend.data);
  return (
    <span
      data-over-cap={String(overCap)}
      className={cn(
        // The bar is 46px tall; two lines of running total do not fit in it.
        "font-mono text-xs whitespace-nowrap",
        overCap ? "text-warn" : "text-muted-foreground",
      )}
    >
      {text}
    </span>
  );
}

export function SpendPage() {
  const spend = useSpend();
  const reading = spend.data && spendLine(spend.data);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Spend</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {spend.isLoading && <Skeleton className="h-8 w-72" />}
        {spend.error && <p className="text-destructive">{String(spend.error)}</p>}
        {reading && (
          <p
            data-over-cap={String(reading.overCap)}
            className={cn("font-mono text-2xl", reading.overCap ? "text-warn" : "text-foreground")}
          >
            {reading.text}
          </p>
        )}
        <p className="text-muted-foreground text-sm">
          Everything spent since midnight UTC, how many of today&apos;s calls could not be priced
          because the model was missing from the price table, and the daily cap this deployment
          configured.
        </p>
      </CardContent>
    </Card>
  );
}
