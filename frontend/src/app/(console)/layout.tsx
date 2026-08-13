/**
 * The console owns the whole viewport: its own top bar, its own tabs, and a
 * browser session embedded inside it. The dashboard chrome would be a second
 * navigation competing with it.
 */
export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
