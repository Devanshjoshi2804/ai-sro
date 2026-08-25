import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { QueryProvider } from "@/lib/query";
import { SignInGate } from "@/features/console/sign-in-gate";
import { Toaster } from "@/components/ui/sonner";
import { EmbeddedCredential } from "@/features/console/embedded-credential";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

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
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
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
