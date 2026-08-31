import { TopBar, BarLink, BarGroup } from "@/features/console/top-bar";

/**
 * The review surfaces: recordings, skills, promotion. Same chrome as the
 * console — a supervisor arriving from a link should recognise the product.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background flex min-h-screen flex-col">
      {/* Grouped by the question each screen answers, not listed alphabetically:
          an operator teaching and a supervisor deciding whether the result may
          run alone never need the same screen at the same time. The bar scrolls
          rather than clipping -- at 560px the last three used to be unreachable,
          with no menu and no way to know they were there. */}
      <TopBar>
        <BarGroup label="Do">
          <BarLink href="/console">Threads</BarLink>
          {/* Beside Threads rather than under Watch: a card here is a decision
              somebody has to make, not a thing to look at. */}
          <BarLink href="/waiting">Waiting on you</BarLink>
        </BarGroup>
        <BarGroup label="Review">
          <BarLink href="/candidates">Candidates</BarLink>
          <BarLink href="/recordings">Recordings</BarLink>
          <BarLink href="/skills">Skills</BarLink>
        </BarGroup>
        <BarGroup label="Watch">
          <BarLink href="/runs">Runs</BarLink>
          <BarLink href="/triggers">Triggers</BarLink>
          <BarLink href="/overview">Overview</BarLink>
        </BarGroup>
        <BarGroup label="Know">
          <BarLink href="/knowledge">What we know</BarLink>
        </BarGroup>
      </TopBar>
      {/* Wider than a reading measure, because these are tables. At `max-w-6xl`
          the Recordings table was 1327px inside an 1104px container -- Frames,
          Narration and Started were off the end -- while 300px of a 1456px
          viewport sat unused beside it. Prose blocks set their own measure. */}
      <main data-chrome="page" className="mx-auto w-full max-w-[1600px] flex-1 px-6 py-8">
        {children}
      </main>
    </div>
  );
}
