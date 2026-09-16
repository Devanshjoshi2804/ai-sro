// Two halves of this panel, and the control that says which one you are on.
//
// It has been one scrolling column: the strip, the day, the cards, the whole
// conversation, and the composer pinned under all of it. That column is what
// "the panel is chaotic" means in practice -- thirteen card states and five row
// types stacked in one place, where a card about a run happening now sits
// between two sentences somebody typed an hour ago.
//
// So: **Home** is what is true right now -- the day, what is waiting, the
// cards, the run. **Chat** is what was said -- the conversation and the box you
// type into. Two panes, one at a time, with one control between them.
//
// **Home is where it opens.** Somebody opening this panel is looking for what
// the system is doing or wants from them, which is a glance; a conversation is
// something you go to. Opening on Chat would put a text box in front of a
// person whose actual question is "did it work".
//
// **The control says what is waiting, and only that.** A count on Home while
// you are reading Chat is the one thing a person on the wrong pane needs to
// know. Nothing counts on Chat: a message that arrived is in a conversation
// that is not going anywhere, and a badge for it is a notification about
// something nobody has to act on.
//
// Pure over what it is given. Which pane is showing lives in the panel, which
// is where a fact about one window of it belongs.

/** The two halves, in the order they are read. */
export const PANES = ["home", "chat"];

/**
 * The control, as a pair of buttons.
 *
 * `waiting` is how many requests nobody has answered; it draws on Home and
 * only while Home is not the pane you are on -- a count beside the thing you
 * are already looking at is a number describing the screen to itself.
 */
export function panes(showing, { waiting = 0, onPick } = {}) {
  const row = document.createElement("div");
  row.className = "panes";
  row.setAttribute("role", "tablist");

  for (const pane of PANES) {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "pane-tab";
    tab.dataset.pane = pane;
    // `aria-selected` and `role=tab` rather than a pressed button: a screen
    // reader then says "Home, tab, 1 of 2, selected", which is the whole
    // control in one sentence.
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-selected", String(pane === showing));
    tab.textContent = pane === "home" ? "Home" : "Chat";
    if (pane === "home" && waiting > 0 && showing !== "home") {
      const count = document.createElement("span");
      count.className = "pane-count";
      count.textContent = String(waiting);
      // Said as well as shown. "Home 3" reads as a heading with a number after
      // it; this is what it means.
      tab.setAttribute("aria-label", `Home, ${waiting} waiting`);
      tab.append(count);
    }
    tab.addEventListener("click", () => onPick?.(pane));
    row.append(tab);
  }
  return row;
}

/**
 * Which pane a thing belongs to, so the panel has one answer rather than a
 * condition per element.
 *
 * Named here rather than in the markup because it is a decision: the composer
 * goes with the conversation, not with the cards, and that is the half of this
 * split somebody will want to argue with.
 */
export const BELONGS = {
  home: ["today", "waiting", "cards"],
  chat: ["thread", "here", "ask-bar"],
};
