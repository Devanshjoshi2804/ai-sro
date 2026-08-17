import { Console } from "@/features/console/console";
import { ThreadProvider } from "@/features/console/thread-store";

/**
 * One conversation, at its own address.
 *
 * Every thread already lived server-side; only the URL was missing, so a
 * reload lost which conversation you were in, the back button did nothing, and
 * a thread could not be sent to a colleague. For a tool whose whole point is
 * that one person's teaching is the team's, that last one is not a small thing.
 */
export default async function ThreadPage({
  params,
}: {
  params: Promise<{ threadId: string }>;
}) {
  const { threadId } = await params;
  return (
    <ThreadProvider>
      <Console threadId={threadId} />
    </ThreadProvider>
  );
}
