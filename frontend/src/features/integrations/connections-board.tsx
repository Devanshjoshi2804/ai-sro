"use client";

import { useState } from "react";
import Nango from "@nangohq/frontend";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createConnectSession,
  displayName,
  integrationKeys,
  listIntegrations,
} from "@/features/integrations/api";
import { ApiError } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const problem = (error: unknown) =>
  error instanceof ApiError ? error.problem.title : "That did not work";

/** One row per mail account the server can connect, and one button to do it. */
export function ConnectionsBoard() {
  const queryClient = useQueryClient();
  const integrations = useQuery({ queryKey: integrationKeys.all, queryFn: listIntegrations });
  // The integration whose session is being made or whose popup is open; one at a time.
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const connect = async (integration: string) => {
    setBusy(integration);
    setFailure(null);
    try {
      const { token, connect_url, api_url } = await createConnectSession(integration);
      new Nango({ connectSessionToken: token }).openConnectUI({
        baseURL: connect_url,
        apiURL: api_url,
        onEvent: (event) => {
          if (event.type === "connect") {
            void queryClient.invalidateQueries({ queryKey: integrationKeys.all });
            setBusy(null);
          } else if (event.type === "close") {
            setBusy(null);
          } else if (event.type === "error") {
            setFailure(`${displayName(integration)} did not connect. Try again.`);
            setBusy(null);
          }
        },
      });
    } catch (error) {
      setFailure(problem(error));
      setBusy(null);
    }
  };

  const list = integrations.data ?? [];
  const message = failure ?? (integrations.isError ? problem(integrations.error) : null);

  return (
    <div className="flex flex-col gap-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-balance">Connections</h1>
        <p className="text-muted-foreground max-w-2xl text-sm">
          Mail accounts the assistant may read and answer from. Connecting opens a sign-in window.
        </p>
      </header>

      {message && (
        <p role="alert" className="text-destructive text-sm">
          {message}
        </p>
      )}

      {integrations.isPending ? (
        <Skeleton className="h-16 w-full" />
      ) : integrations.isSuccess && list.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No mail accounts can be connected on this server yet.
        </p>
      ) : (
        <ul className="divide-border divide-y rounded-md border">
          {list.map((item) => {
            const name = displayName(item.integration);
            return (
              <li key={item.integration} className="flex items-center justify-between gap-4 p-4">
                <span>
                  {item.connected ? (
                    <>
                      {name} — Connected
                      {item.connected_at && (
                        <span className="text-muted-foreground text-sm">
                          {" "}
                          since{" "}
                          <time dateTime={item.connected_at}>
                            {new Date(item.connected_at).toLocaleString()}
                          </time>
                        </span>
                      )}
                    </>
                  ) : (
                    `${name} — not connected`
                  )}
                </span>
                {!item.connected && (
                  <Button
                    type="button"
                    disabled={busy !== null}
                    aria-busy={busy === item.integration}
                    onClick={() => void connect(item.integration)}
                  >
                    {busy === item.integration ? `Connecting ${name}…` : `Connect ${name}`}
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
