import { TopBar, BarLink, BarGroup } from "@/features/console/top-bar";
import { AwaitingBadge } from "@/features/workflow/components/awaiting-badge";
import { SpendLine } from "@/features/workflow/components/spend-line";

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
          {/* The badge rather than the link is what has to be seen: a parked run
              is a live Chrome holding a warehouse write open, and it is waiting
              whichever of these five pages somebody happens to be standing on.
              It renders nothing when the count is zero. */}
          <BarLink href="/needs">
            Needs a person
            <AwaitingBadge />
          </BarLink>
        </BarGroup>
        <BarGroup label="Review">
          {/* First: this is where a run is started, so it is the one a
              supervisor reaches for before the three that judge what came
              back. `BarLink` matches by prefix, so it stays lit on
              /jobs/runs/<id>. */}
          <BarLink href="/jobs">Jobs</BarLink>
          <BarLink href="/candidates">Candidates</BarLink>
          <BarLink href="/recordings">Recordings</BarLink>
          <BarLink href="/skills">Skills</BarLink>
        </BarGroup>
        <BarGroup label="Watch">
          <BarLink href="/runs">Runs</BarLink>
          <BarLink href="/triggers">Triggers</BarLink>
          <BarLink href="/overview">Overview</BarLink>
          <BarLink href="/browsers">Browsers</BarLink>
          <BarLink href="/audit">Audit</BarLink>
          <BarLink href="/spend">Spend</BarLink>
        </BarGroup>
        <BarGroup label="Know">
          <BarLink href="/knowledge">What we know</BarLink>
        </BarGroup>
        {/* Last child of the bar, left of the spacer, rather than a `right`
            prop on TopBar: every surface in the application shares that
            component and one line of running total does not justify widening
            its interface. It renders nothing while loading and nothing on
            error, so the bar is unchanged when the number cannot be trusted.
            The wrapper is here and not in the component because the bar lays
            its children out `stretch`, and a bare span would hang its text off
            the top edge. */}
        <span
          style={{ display: "flex", alignItems: "center", paddingLeft: 18, flex: "0 0 auto" }}
        >
          <SpendLine />
        </span>
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
