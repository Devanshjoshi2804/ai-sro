import type { Metadata } from "next";
import { Space_Grotesk, Geist, JetBrains_Mono } from "next/font/google";
import { QueryProvider } from "@/lib/query";
import { SignInGate } from "@/features/console/sign-in-gate";
import { Toaster } from "@/components/ui/sonner";
import { EmbeddedCredential } from "@/features/console/embedded-credential";
import "./globals.css";

// The brand's three. Manrope was named in the top bar and JetBrains Mono in the
// console's palette, and neither was ever loaded -- both fell back silently.
// Mono is not decoration here: it carries every number that changes while
// somebody watches it, and every id, host and call. The body face is Geist, as
// the extension's panel is (Ember & Glass), so the two surfaces read as one.
const display = Space_Grotesk({ variable: "--font-display", subsets: ["latin"] });
const body = Geist({ variable: "--font-body", subsets: ["latin"] });
const mono = JetBrains_Mono({ variable: "--font-mono-face", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI-SRO",
  description: "Demonstrations in, reviewable skills out.",
};

/**
 * Only what every route needs. Navigation belongs to the route group that wants
 * it: the console owns its whole viewport and supplies its own.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // `dark` is set here and never toggled. The brand commits to one theme, and
    // the shadcn primitives carry `dark:` variants tuned for a dark ground --
    // switching the variant on is what keeps `components/ui/` untouched, which
    // the CLI overwrites on update.
    <html
      lang="en"
      className={`dark ${display.variable} ${body.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="bg-background text-foreground flex min-h-full flex-col">
        {/* Before hydration, so a 400px panel never paints a top bar and a
            772px column and then collapses them. Framed *is* embedded: the
            frame-ancestors header means only the extension can be the frame.
            Comparing `top` cross-origin returns an opaque handle and never
            throws. If a `script-src` is ever added, this needs a nonce. */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              'if(self!==top||location.search.includes("embedded=1"))' +
              'document.documentElement.dataset.embedded=""',
          }}
        />
        <QueryProvider>
          {/* Nothing renders until this browser holds a credential: every
              screen below reads a tenant's recordings and can authorise a
              write into their warehouse. */}
          <SignInGate>{children}</SignInGate>
          {/* Only ever does anything inside the extension's side panel, and
              only for the origins that panel was configured with. */}
          <EmbeddedCredential />
          <Toaster />
        </QueryProvider>
      </body>
    </html>
  );
}
