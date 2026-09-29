// A pill in the corner of the page, for an offer nobody can see.
//
// In a shadow root because it is drawn over somebody else's application. The
// WMS has its own reset, its own z-index ladder and its own opinions about
// `*`, and a pill that inherited any of them would be one the operator reports
// as a rendering bug.

/** How long a nudge's pill stays up. `LIFETIME_MS` in `panel/nudge.js` owns the
 * rule; this is the same number, because the pill and the entry in the ledger
 * are one prompt and must not outlive each other. */
const LIFETIME_MS = 90_000;

const NUDGE_ID = "sro-nudge";

/** A pill in the corner of the page, for a nudge nobody can see.
 *
 * The panel may be closed. An offer drawn only in a panel nobody has open is an
 * offer nobody was made, and the whole point of a nudge is that it arrives at
 * the moment somebody is about to do the thing themselves.
 *
 * A pill and not a dialog. It sits in the corner of somebody else's
 * application, takes no focus, blocks nothing, and clicking it opens the panel
 * -- where the offer is, with its two answers. It never runs anything itself:
 * the press that authorises a run happens where the operator can read what they
 * are authorising.
 */
export async function showNudge(tabId, title) {
  if (tabId === null || tabId === undefined) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: paintNudge,
      args: [NUDGE_ID, String(title || ""), LIFETIME_MS],
    });
  } catch {
    // A tab that closed, or one this extension may not touch. Nothing is lost:
    // the nudge is in the panel either way, and it expires on its own.
  }
}

export async function hideNudge(tabId) {
  if (tabId === null || tabId === undefined) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (id) => document.getElementById(id)?.remove(),
      args: [NUDGE_ID],
    });
  } catch {
    // As above.
  }
}

/** Runs in the page. Closes over nothing; everything it needs is an argument. */
function paintNudge(id, title, lifetimeMs) {
  document.getElementById(id)?.remove();
  const host = document.createElement("div");
  host.id = id;
  host.style.cssText =
    "all:initial;position:fixed;top:12px;right:12px;z-index:2147483646;pointer-events:none";
  const shadow = host.attachShadow({ mode: "open" });
  const pill = document.createElement("button");
  pill.type = "button";
  pill.style.cssText =
    "font:500 12px/1.3 system-ui,-apple-system,'Segoe UI',sans-serif;" +
    "pointer-events:auto;cursor:pointer;border:0;border-radius:999px;" +
    // The accent's dark end: white on the brand accent itself is 3.8:1 and
    // fails AA at this size; this is 5.2:1, as the panel's own buttons are.
    "padding:8px 14px;color:#fff;background:linear-gradient(180deg,#c2410c,#b83c0f);" +
    "box-shadow:inset 0 1px 0 rgba(255,255,255,.24),0 0 0 4px rgba(220,88,42,.14)," +
    "0 10px 24px -8px rgba(0,0,0,.55)";
  // `textContent`, never markup: the title is a task name derived from calls
  // the operator's own browser made, which is to say from the open internet.
  pill.textContent = title ? `AI-SRO · do \u201c${title}\u201d?` : "AI-SRO · do this one?";
  pill.addEventListener("click", () => {
    host.remove();
    chrome.runtime.sendMessage({ kind: "open-panel" });
  });
  shadow.append(pill);
  document.documentElement.appendChild(host);

  // It takes itself away: everything else that could remove it -- the
  // worker, the panel, an alarm -- can be gone.
  setTimeout(() => host.remove(), Number(lifetimeMs) || 90000);
}
