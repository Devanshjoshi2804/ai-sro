import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import { QueryProvider } from "@/lib/query";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI-SRO",
  description: "Demonstrations in, reviewable skills out.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="bg-background text-foreground flex min-h-full flex-col">
        <QueryProvider>
          <header className="border-b">
            <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
              <Link href="/" className="font-semibold tracking-tight">
                AI-SRO
              </Link>
              <Link
                href="/recordings"
                className="text-muted-foreground hover:text-foreground text-sm"
              >
                Recordings
              </Link>
              <Link href="/skills" className="text-muted-foreground hover:text-foreground text-sm">
                Skills
              </Link>
            </nav>
          </header>
          <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
          <Toaster />
        </QueryProvider>
      </body>
    </html>
  );
}
