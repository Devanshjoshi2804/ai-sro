import { ConsoleErrorBoundary } from "@/features/console/error-boundary";

/**
 * The console owns the whole viewport: its own top bar, its own tabs, and a
 * browser session embedded inside it. The dashboard chrome would be a second
 * navigation competing with it.
 *
 * Wrapped, because the transcript in it exists nowhere else: a render that
 * throws anywhere below here used to unmount all of it.
 */
export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleErrorBoundary>{children}</ConsoleErrorBoundary>;
}
