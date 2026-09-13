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
      {/* The running total rides in `right`, beside the tenant, rather than
          among the links: those scroll and it must not. It renders nothing
          while loading and nothing on error, so the bar is unchanged whenever
          the number cannot be trusted. */}
      <TopBar
        right={
          <span style={{ display: "flex", alignItems: "center", paddingLeft: 18 }}>
            <SpendLine />
          </span>
        }
      >
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
              supervisor reaches for before what judges it. `BarLink` matches
              by prefix, so it stays lit on /jobs/runs/<id>.

              Candidates and Skills were here and are gone. Both were the
              pre-rig path: `MineObservations` clustered `observations` into
              `task_candidates` and `LearnWhatRepeats` taught them, and that
              sweep is off -- four of the nine skills it taught across both
              real tenants were not work, two of them this console's own Learn
              button. With it off, Candidates was a permanently empty page
              whose one action triggered something the rig now does on its own.

              Recordings stays: a deliberate demonstration is still a thing an
              operator does, and the rig's own uploads write those rows. */}
          <BarLink href="/jobs">Jobs</BarLink>
          <BarLink href="/recordings">Recordings</BarLink>
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
