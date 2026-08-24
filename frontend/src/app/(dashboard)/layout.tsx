import { TopBar, BarLink } from "@/features/console/top-bar";

/**
 * The review surfaces: recordings, skills, promotion. Same chrome as the
 * console — a supervisor arriving from a link should recognise the product.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col" style={{ background: "#F6F6F4" }}>
      <TopBar>
        <BarLink href="/console">Threads</BarLink>
        <BarLink href="/overview">Overview</BarLink>
        <BarLink href="/recordings">Recordings</BarLink>
        <BarLink href="/skills">Skills</BarLink>
        <BarLink href="/runs">Runs</BarLink>
        <BarLink href="/knowledge">What we know</BarLink>
      </TopBar>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
    </div>
  );
}
