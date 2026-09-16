// What arrived while nobody was looking.
//
// The Home half of this panel is a stack of cards, each one a thing that is
// true right now: a job being offered, a run happening, a question waiting on
// an answer. That stack is only readable while it is short, which is the whole
// reason an offer ends rather than accumulating.
//
// A request that came in by mail breaks that rule on purpose -- it is kept
// until somebody answers it, because the backend offers each message exactly
// once and a swept card is work silently dropped. So three mails over a
// morning are three cards that cannot be swept, in a column where four cards
// is already a lot.
//
// This is where they go instead: one line at the top, folded, with the number
// on it. Open it and the cards themselves drop down, identical to the ones in
// the stack and pressable in place. Answer one and it leaves; answer them all
// and the line goes with them.
//
// Three decisions worth arguing with:
//
// **Folded by default.** The number is what somebody coming back to the panel
// needs first, and the detail is one tap behind it. A banner that unfolded
// itself would be four cards in the eye line of somebody who came to the panel
// to do something else.
//
// **The count, always, even at one.** The alternative -- show a lone card in
// the stack and only fold from two -- means a card that moves depending on how
// many of its kind exist, and an operator who saw one yesterday looking for it
// in the wrong place today.
//
// **Attention, never the accent.** `brand.css` says state colours are not the
// accent, and this is a state. It reuses the `data-tone` enum the cards
// already have rather than inventing a class of its own.
//
// Pure over what it is given: no storage, no clock, no chrome. The panel holds
// whether it is open, because that is a fact about one window of it.

/**
 * The banner, or `null` when nothing is waiting.
 *
 * `missed` is the offers nobody has answered that have stopped being today's
 * news. `open` is this window's own state, `onToggle` is how it says the
 * operator flipped it, and `card` builds one card -- injected rather than
 * imported so this file can be read, and tested, without the ledger behind it.
 */
export function waiting(missed, { open = false, onToggle, card } = {}) {
  if (!missed.length) return null;

  const box = document.createElement("section");
  box.className = "card";
  box.dataset.tone = "attention";
  box.dataset.waiting = String(missed.length);

  // The whole line is the control. A chevron is a four-pixel target on a panel
  // somebody is using one-handed beside a warehouse system.
  const head = document.createElement("button");
  head.type = "button";
  head.className = "waiting-head";
  head.setAttribute("aria-expanded", String(open));
  const said = document.createElement("span");
  said.className = "what";
  said.textContent =
    missed.length === 1
      ? "1 request arrived while you were away."
      : `${missed.length} requests arrived while you were away.`;
  const how = document.createElement("span");
  how.className = "note";
  how.textContent = open ? "Hide" : "Show";
  head.append(said, how);
  head.addEventListener("click", () => onToggle?.(!open));
  box.append(head);

  if (open && card) {
    const list = document.createElement("div");
    list.className = "waiting-list";
    // Newest first: the request that came in ten minutes ago is the one they
    // are most likely to have been told about by the person who sent it.
    for (const one of [...missed].sort((a, b) => String(b.at || "").localeCompare(String(a.at || "")))) {
      list.append(card(one));
    }
    box.append(list);
  }

  return box;
}
