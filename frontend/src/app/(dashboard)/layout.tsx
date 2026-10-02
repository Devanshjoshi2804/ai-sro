import { TopBar, BarLink } from "@/features/console/top-bar";

/**
 * Everything that is not the conversation. Same chrome as the console, and the
 * same five places in the same order, so the bar is one navigation rather than
 * two that disagree.
 *
 * Five, where there were twelve in four groups. What went, and where its
 * question is answered now:
 *
 * - Jobs is the first half of What we know: what this tenant can do and what it
 *   knows about its systems are read together, and a job's detail page and a
 *   run's keep their addresses because the extension links to both.
 * - Needs a person and Waiting on you are answered in the extension's panel, in
 *   the browser actually holding the write open. A card here was a second place
 *   to answer one question, and the one further from the screen it was about.
 * - Recordings, Runs and Browsers went with teaching in a browser on the server.
 * - Audit and Spend, and the day's running total that sat on the right of
 *   this bar.
 *
 * `next.config.ts` redirects every removed address, so a bookmark lands
 * somewhere that answers what it used to.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background flex min-h-screen flex-col">
      <TopBar>
        <BarLink href="/console">Threads</BarLink>
        <BarLink href="/knowledge" also={["/jobs"]}>
          What we know
        </BarLink>
        <BarLink href="/triggers">Triggers</BarLink>
        <BarLink href="/connections">Connections</BarLink>
        <BarLink href="/overview">Overview</BarLink>
      </TopBar>
      {/* Wider than a reading measure, because these are tables. Prose blocks
          set their own measure. */}
      <main data-chrome="page" className="mx-auto w-full max-w-[1600px] flex-1 px-6 py-8">
        {children}
      </main>
    </div>
  );
}
