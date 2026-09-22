// A band across the page while a run is driving it.
//
// The side panel already says "a run is performing here", with the step count
// and a button to stop it. The panel is not where somebody is looking: they are
// looking at the page, watching fields fill and buttons press, and nothing
// there says it is not them, or a colleague on the same account, or the
// application having a moment.
//
// So the tab being driven says so itself. Not a notification and not a dialog:
// a band at the top of the document that is there for exactly as long as the
// driving is, naming the task and offering to stop it.
//
// In a shadow root because it is drawn over somebody else's application. The
// WMS has its own reset, its own z-index ladder and its own opinions about
// `*`, and a banner that inherited any of them would be a banner the operator
// reports as a rendering bug.

const BANNER_ID = "sro-driving-banner";

/** How long a nudge's pill stays up. `LIFETIME_MS` in `panel/nudge.js` owns the
 * rule; this is the same number, because the pill and the entry in the ledger
 * are one prompt and must not outlive each other. */
const LIFETIME_MS = 90_000;

/** What the band says.
 *
 * Composed here rather than in `paint`, which is serialised into the page and
 * closes over nothing -- anything it worked out itself would be untestable by
 * construction. This is the whole message a person reads about why their screen
 * is moving, so it is the part worth checking.
 *
 * A step nobody named still gets a band: the vision rung asks for a driver
 * before it knows which gesture it will propose, and "something is driving this
 * tab" is worth more than silence while that is decided.
 */
export function sentence({ skill, step, of }) {
  const doing = skill ? `AI-SRO is doing \u201c${skill}\u201d` : "AI-SRO is working in this tab";
  if (!step) return doing;
  // "step 4" without a total when the total is unknown -- a denominator this
  // code invented would be read as a promise about how long it has left.
  return of ? `${doing} \u2014 step ${step} of ${of}` : `${doing} \u2014 step ${step}`;
}

/** Put the band in the tab, or update what it says.
 *
 * Injected rather than shipped in the content script: the recorder is
 * registered by policy and may not be in this tab at all, and a run drives
 * whatever tab the step names.
 */
export async function showDriving(tabId, { skill, step, of, runId, quietMs }) {
  if (tabId === null || tabId === undefined) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: paint,
      args: [BANNER_ID, { said: sentence({ skill, step, of }), runId, quietMs }],
    });
  } catch {
    // A tab that closed, or one Chrome will not let anyone script. The run is
    // the thing that matters and it carries on; a missing banner is not worth
    // failing a step over.
  }
}

export async function hideDriving(tabId) {
  if (tabId === null || tabId === undefined) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (id) => document.getElementById(id)?.remove(),
      args: [BANNER_ID],
    });
  } catch {
    // As above.
  }
}

/** Runs in the page. Everything it needs is an argument, because this function
 * is serialised across and closes over nothing. */
function paint(id, run) {
  const existing = document.getElementById(id);
  const host = existing || document.createElement("div");

  if (!existing) {
    host.id = id;
    // `max` rather than a number somebody picked: this has to sit over an
    // application whose own dialogs are already at 10000-and-something, and
    // losing that race means the band is behind the thing being driven.
    host.style.cssText =
      "all:initial;position:fixed;top:0;left:0;right:0;z-index:2147483647;pointer-events:none";
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        /* Ember & Glass: smoked glass over the page, an ember rail down its
           left edge, and the one thing it lets you do -- stop -- in the red
           that means only you can do this. */
        .band {
          position: relative;
          font: 500 12.5px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
          display: flex; align-items: center; gap: 12px;
          padding: 10px 14px 10px 17px; color: #e1e4e9;
          background: rgba(12, 13, 17, .86);
          -webkit-backdrop-filter: blur(14px) saturate(140%);
          backdrop-filter: blur(14px) saturate(140%);
          border-bottom: 1px solid rgba(220, 88, 42, .35);
          box-shadow: 0 18px 40px -20px rgba(0, 0, 0, .6);
          pointer-events: auto;
        }
        .band::before {
          content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
          background: linear-gradient(#ff8452, #c2410c);
        }
        .dot {
          width: 16px; height: 16px; border-radius: 50%; flex: none;
          border: 1.5px solid rgba(220, 88, 42, .25); border-top-color: #ff8452;
          animation: spin 1s cubic-bezier(.5, .1, .5, .9) infinite;
        }
        /* Movement, because a band that could be a screenshot is a band
           somebody stops believing. Reduced-motion turns it off: the colour
           and the words carry the message on their own. */
        @keyframes spin { to { transform: rotate(360deg) } }
        @media (prefers-reduced-motion: reduce) { .dot { animation: none } }
        .said {
          flex: 1; min-width: 0; color: #f4f5f7;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        button {
          flex: none; font: inherit; height: 30px; padding: 0 14px;
          border-radius: 999px; cursor: pointer; color: #fecaca;
          background: rgba(248, 113, 113, .12);
          border: 1px solid rgba(248, 113, 113, .35);
        }
        button:hover { background: rgba(248, 113, 113, .2) }
        button:disabled { opacity: .6; cursor: default }
      </style>
      <div class="band">
        <span class="dot"></span>
        <span class="said"></span>
        <button type="button">Stop this run</button>
      </div>`;
    shadow.querySelector("button").addEventListener("click", (event) => {
      const pressed = event.currentTarget;
      pressed.disabled = true;
      // What is already inside the page finishes; this stops the next step,
      // which is what the button says once it has been pressed.
      pressed.textContent = "stopping…";
      chrome.runtime.sendMessage({ kind: "abort-run", runId: run.runId });
    });
    document.documentElement.appendChild(host);
  }

  host.shadowRoot.querySelector(".said").textContent = run.said;

  // The band takes itself away if nothing refreshes it.
  //
  // Every other way of removing it depends on something outside this page
  // still being alive: the worker that put it here can be evicted mid-run, the
  // panel that polls may be closed, and the socket can drop. A band still
  // claiming a run is happening after it stopped is worse than no band at all
  // -- it teaches somebody to disbelieve the one thing that is supposed to tell
  // them the truth about their own screen.
  clearTimeout(host.dataset.timer);
  host.dataset.timer = String(
    setTimeout(() => host.remove(), Number(run.quietMs) || 30000),
  );
}


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

  // It takes itself away, for the reason the driving band does: everything else
  // that could remove it -- the worker, the panel, an alarm -- can be gone.
  setTimeout(() => host.remove(), Number(lifetimeMs) || 90000);
}
