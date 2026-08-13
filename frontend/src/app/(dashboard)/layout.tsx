import Link from "next/link";

/** The review screens: list, detail, promote. The console has its own chrome. */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header className="border-b">
        <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
          <Link href="/console" className="font-semibold tracking-tight">
            AI-SRO
          </Link>
          <Link href="/recordings" className="text-muted-foreground hover:text-foreground text-sm">
            Recordings
          </Link>
          <Link href="/skills" className="text-muted-foreground hover:text-foreground text-sm">
            Skills
          </Link>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
    </>
  );
}
