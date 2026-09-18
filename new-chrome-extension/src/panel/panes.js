// Where you can go in this panel, as a cluster of icons rather than a row.
//
// It has been one scrolling column: the strip, the day, the cards, the whole
// conversation, and the composer pinned under all of it. That column is what
// "the panel is chaotic" means in practice -- thirteen card states and five row
// types stacked in one place, where a card about a run happening now sits
// between two sentences somebody typed an hour ago.
//
// So: **Home** is what is true right now -- the day, what is waiting, the
// cards, the run. **Chat** is what was said -- the conversation, and the box
// you type into is under both of them.
//
// **Icons, in the strip, not a row of their own.** Two word-tabs across the
// top spent a whole row of a 360-pixel panel saying where you are, above a
// second row saying which tab you are docked beside. A panel beside a
// warehouse screen has about six rows of usable height. The cluster sits in
// the strip that was already there, each control named to anything that cannot
// see a glyph -- `title` for the pointer, `aria-label` for the reader.
//
// **Home is where it opens.** Somebody opening this panel is looking for what
// the system is doing or wants from them, which is a glance; a conversation is
// something you go to.
//
// **The count says what is waiting, and only that.** A count on Home while you
// are reading Chat is the one thing a person on the wrong pane needs to know.
// Nothing counts on Chat: a message that arrived is in a conversation that is
// not going anywhere, and a badge for it is a notification about something
// nobody has to act on.
//
// Pure over what it is given. Which pane is showing lives in the panel, which
// is where a fact about one window of it belongs.

/** The two halves, in the order they are read. */
export const PANES = ["home", "chat"];

/** Every control in the cluster, in order.
 *
 * `pane` is set on the two that switch halves, so the tablist semantics stay
 * on exactly those two; the other two are ordinary buttons that do a thing.
 * History and New are buttons and not panes on purpose -- history is an
 * overlay you close and come back from, and a new conversation is an action,
 * not a place.
 */
const CONTROLS = [
  { key: "home", pane: true, glyph: "⌂", says: "Home" },
  { key: "chat", pane: true, glyph: "☷", says: "Chat" },
  { key: "pending", glyph: "▤", says: "Waiting for you" },
  { key: "history", glyph: "⏱", says: "Recent tasks" },
  { key: "new", glyph: "＋", says: "New conversation" },
];

/**
 * The cluster.
 *
 * `waiting` is how many requests nobody has answered; it draws on Home and
 * only while Home is not the pane you are on -- a count beside the thing you
 * are already looking at is a number describing the screen to itself.
 *
 * `onPick` is told which control was pressed: `home`, `chat`, `history`, `new`.
 */
export function panes(showing, { waiting = 0, onPick } = {}) {
  const row = document.createElement("div");
  row.className = "panes";
  row.setAttribute("role", "tablist");

  for (const { key, pane, glyph, says } of CONTROLS) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "pane-tab";
    tab.dataset.pane = key;
    tab.textContent = glyph;
    // A glyph is not a name. The pointer gets the word on hover and anything
    // that reads the page gets it always -- without which this is four
    // unlabelled shapes, which is what an icon row is when nobody says what
    // the icons are.
    tab.title = says;
    tab.setAttribute("aria-label", says);
    if (pane) {
      // `aria-selected` and `role=tab` rather than a pressed button: a screen
      // reader then says "Home, tab, 1 of 2, selected", which is the whole
      // control in one sentence.
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(key === showing));
    }
    // The count rides on the tray, and on the tray only.
    //
    // It was on Home, and drawn only while you were on Chat -- which was right
    // when everything waiting WAS on Home. It is not any more: Home keeps the
    // newest one and the rest are in here, so a number on Home would be
    // counting things that are not on it. Shown on whichever pane you are
    // standing on, because the backlog is behind a door either way.
    if (key === "pending" && waiting > 0) {
      const count = document.createElement("span");
      count.className = "pane-count";
      count.textContent = String(waiting);
      // Said as well as shown. A number sitting on a glyph reads as a badge
      // and nothing else; this is what it means.
      tab.setAttribute("aria-label", `Waiting for you, ${waiting}`);
      tab.append(count);
    }
    tab.addEventListener("click", () => onPick?.(key));
    row.append(tab);
  }
  return row;
}
