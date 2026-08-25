"use client";

import { useEffect } from "react";
import { credential, looksLikeAToken, remember } from "@/lib/api/credential";
import { env } from "@/lib/env";

/**
 * Takes a credential from the browser extension's side panel, and from nothing
 * else.
 *
 * The console keeps its token in `localStorage`, and Chrome partitions storage
 * for framed third-party contexts -- so a console rendered inside the panel
 * cannot see the token from its own tab, even though the same person pasted it
 * minutes ago. It has to be handed across, and handing a credential between
 * origins is the kind of thing that is either exactly right or a hole.
 *
 * Three refusals, in this order, and each closes something specific:
 *
 * 1. Not framed -- no listener is registered at all. A console open in an
 *    ordinary tab must have no way to be handed a credential, because then any
 *    page that can reach it becomes a credential injector. Checked before
 *    `addEventListener` rather than inside the handler, so the capability does
 *    not exist rather than being declined.
 * 2. No configured extension origins -- no listener either. A deployment that
 *    does not use the panel gets the safe default without doing anything.
 * 3. A message from anywhere else, or carrying anything that is not a token --
 *    ignored in silence. Silence rather than a refusal on purpose: a reply that
 *    distinguished "wrong origin" from "bad token" would make this an oracle
 *    for probing what the console accepts.
 */
export function EmbeddedCredential() {
  useEffect(() => {
    if (window.self === window.top) return;

    const allowed = extensionOrigins();
    if (!allowed.length) return;

    function receive(event: MessageEvent) {
      if (!allowed.includes(event.origin)) return;

      const message = event.data as { kind?: unknown; token?: unknown } | null;
      if (!message || message.kind !== "sro.credential") return;
      if (typeof message.token !== "string" || !looksLikeAToken(message.token)) return;

      // Only when it is actually different: `remember` announces, and an
      // announcement re-renders the gate and everything under it.
      if (message.token.trim() !== credential()) remember(message.token);

      // Answered to the sender's own origin, never "*". The panel has no other
      // way to tell "handed over" from "silently refused" -- a cross-origin
      // frame does not report its own failures to the page that framed it.
      event.source?.postMessage({ kind: "sro.credential.ok" }, { targetOrigin: event.origin });
    }

    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);

  return null;
}

/** The extension origins this deployment accepts a credential from.
 *
 * Empty unless somebody configured it, which is what makes "no panel here"
 * the default rather than something to remember to switch off.
 */
function extensionOrigins(): string[] {
  return env.NEXT_PUBLIC_EXTENSION_ORIGINS.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
}
