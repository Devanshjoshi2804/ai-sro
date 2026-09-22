// The top of the panel: who this is, which tab it is beside, and what is
// happening to that tab.
//
// It used to be a card. "Not watching this tab", a paragraph, and two buttons,
// on every tab an operator switched to -- a permission gate standing in front
// of the thing they opened the panel for, all day, including on tabs nobody
// would ever watch. Being on a tab that is not evidence is the ordinary case.
//
// So it is a line. The chevron opens it to the card that exists today, and the
// line opens itself only in the four states where there is something to press.
// Everything rare and deliberate -- pause, purge, settings, disconnect -- is
// under the profile, out of the way of the one control reached hourly.
//
// A pure function of state to DOM, like `ledger.js`: no fetching, no timers,
// no `chrome.*`. What a press means is the caller's to decide, which is what
// makes the rules here testable in plain node.

/** What each item in the profile menu is called, and what it answers with.
 *
 * `action` is a word about the deployment rather than about the button, so a
 * caller wiring it up is not reading a label to decide what happened.
 */
const MENU = [
  // The console in a tab of its own. It was a button in the strip until the
  // navigation cluster took that space, and it belongs here: opening the
  // console is a thing done occasionally and deliberately, which is what this
  // menu is for.
  { action: "console", label: "Console ↗" },
  // The console in the tab beside the panel, in place of the page there. It
  // was framed inside the panel: a 360-pixel console behind a credential
  // handshake that needed a line of configuration per extension, for a screen
  // that is a full-width application.
  { action: "console-here", label: "Open the console here" },
  { action: "purge", label: "Delete the last hour" },
  { action: "never", label: "Never watch this site" },
  { action: "settings", label: "Settings" },
  { action: "disconnect", label: "Disconnect this browser" },
];

/**
 * Why this line must open itself, or `null` when it is only a line.
 *
 * Four states, and the rule for all four is the same: there is something here
 * only the operator can fix. Everything else -- watched, not watched, paused,
 * recording -- is a fact about their browser that a line states and a card
 * would nag about.
 *
 * A closed channel on its own is not one of them. The channel closes whenever
 * the worker sleeps, which is most of the day; it matters when something is
 * trying to drive this browser and cannot. Opening on it alone would have the
 * panel crying wolf hourly, which is how a warning stops being read.
 */
export function needsAPress(status, here) {
  if (!status.deviceId) return "not-connected";
  if (status.grantExpired) return "grant";
  if (status.channel !== "open" && status.performing) return "channel";
  if (status.excludedHere) return "excluded";
  void here;
  return null;
}

/** What is happening to the tab beside the panel, as a word and a sentence. */
function stateOf(status, here) {
  if (status.teaching) {
    const elapsed = status.teaching.elapsed
      ? ` ${status.teaching.elapsed}`
      : "";
    return ["recording", `recording a demonstration${elapsed}`];
  }
  if (status.paused || status.serverPaused) return ["paused", "paused"];
  const watchedHere = (status.watched || []).some(
    (tab) => tab.tabId === here.tabId,
  );
  if (status.capturing && watchedHere) {
    return [
      "observing",
      `watching${status.since ? ` ${forHowLong(status.since)}` : ""}`,
    ];
  }
  return ["idle", "not watched"];
}

/** Minutes until an hour and a half, then hours. Nobody reads "127 min". */
function forHowLong(since) {
  const minutes = Math.max(
    0,
    Math.round((Date.now() - new Date(since).getTime()) / 60000),
  );
  if (Number.isNaN(minutes)) return "";
  return minutes >= 90 ? `${Math.round(minutes / 60)} h` : `${minutes} min`;
}

/**
 * The strip.
 *
 * `onMenu(action)` is called with one of `console`, `pause`, `resume`, `purge`,
 * `never`, `settings`, `disconnect`. `onToggle()` is called when the operator
 * opens or closes the chip themselves -- what that reveals is the caller's, so
 * the expanded card stays where its state machine already lives.
 */
export function strip(status, here, { onMenu, onToggle, nav } = {}) {
  const root = document.createElement("header");
  root.className = "strip";

  const brand = document.createElement("div");
  brand.className = "brand";
  const mark = document.createElement("span");
  mark.className = "mark";
  mark.textContent = "g";
  const name = document.createElement("span");
  name.className = "name";
  name.textContent = "AI-SRO";

  const disc = document.createElement("button");
  disc.type = "button";
  disc.className = "disc";
  disc.textContent = (status.principal || "?").slice(0, 1).toUpperCase();
  // The navigation, in the row that was already here.
  //
  // It used to be two word-tabs on a row of their own, under this one: a
  // 360-pixel panel beside a warehouse screen has about six rows of usable
  // height and two of them were spent saying where you are. The cluster is an
  // element this file is GIVEN rather than one it builds -- the panel owns it,
  // so the strip redrawing every couple of seconds does not rebuild the
  // buttons under somebody's cursor.
  //
  // "Console" left with it, into the menu behind the disc, where the rest of
  // the once-a-week things already are.
  brand.append(mark, name, ...(nav ? [nav] : []), disc);

  const menu = document.createElement("div");
  menu.className = "menu";
  menu.hidden = true;
  const paused = Boolean(status.paused);
  const items = [
    {
      action: paused ? "resume" : "pause",
      label: paused ? "Resume watching" : "Pause watching",
    },
    ...MENU,
  ];
  for (const { action, label } of items) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    // The one entry that destroys evidence is red at rest, not only on hover.
    if (action === "purge") button.dataset.danger = "true";
    button.addEventListener("click", () => {
      // Closed before the caller hears about it. A menu still open behind a
      // dialog, or behind a panel that just redrew, is the one somebody
      // presses twice.
      menu.hidden = true;
      onMenu?.(action);
    });
    menu.append(button);
  }
  disc.addEventListener("click", () => {
    menu.hidden = !menu.hidden;
  });

  const chip = document.createElement("button");
  chip.type = "button";
  chip.className = "chip";
  const [state, says] = stateOf(status, here);
  chip.dataset.state = state;
  // A panel that does not name the tab it is docked beside leaves the operator
  // to assume, and the tab they are looking at is not always this one.
  const host = document.createElement("span");
  host.className = "host";
  host.textContent = here.host || "—";
  const what = document.createElement("span");
  what.className = "says";
  what.textContent = says;
  chip.append(host, what);

  const why = needsAPress(status, here);
  chip.dataset.open = String(why !== null);
  chip.dataset.why = why || "";
  chip.addEventListener("click", () => onToggle?.());

  root.append(brand, menu, chip);
  return root;
}
