// One thread, drawn.
//
// The panel used to say what it had to say in cards: a card appeared, and when
// the panel closed it was gone. An offer -- "you've done this 3 times, want me
// to do the next one?" -- is not a card. It is something the system said, and
// the operator's answer belongs beside it, in the same place, still there
// tomorrow. So the panel renders a thread that lives on the server, and this
// file is the whole of how a thread becomes DOM.
//
// Two properties this file exists to hold, in this order:
//
// 1. No `innerHTML`, anywhere. Every word here is either typed by an operator
//    or written by a model, and both arrive over the wire. `textContent` is
//    the only way text is put on the page; a string that looks like markup is
//    shown as the string it is. This is a security boundary and not a style
//    preference -- the panel runs in an extension origin with `chrome.*` in
//    reach.
//
// 2. A message is a thing said; the press is the authorisation. Drawing an
//    offer starts nothing. The buttons hand the answer back to the caller,
//    which makes the same call the panel has always made, and that press is
//    what an assisted run records as its consent.
//
// A pure function of a thread to DOM: no fetching, no state, no timers. That
// is what makes it testable in plain node against a fake document, which is
// what `ledger.test.mjs` does.

/** What the console's composer says, said here. The panel's own way of asking
 * for a task is this box now, so its prompt is the one the console already
 * uses rather than a second wording of the same invitation. */
const ASKING = "Ask for a task — or say what you're doing";

/** The answers an offer can be given, and which button is the quiet one.
 *
 * The same two the candidate rows show today, because pressing one runs the
 * same code path they do. `answer` is what reaches `onPress`, and it is a word
 * about the conversation ("do", "no") rather than about the button, so a
 * caller wiring it up is not reading a label to decide what happened.
 */
const ANSWERS = [
  { answer: "do", label: "Do the next one", quiet: false },
  { answer: "no", label: "Not now", quiet: true },
];

/** What each kind of thing said offers to do about it.
 *
 * One table rather than a branch per kind further down: the panel and the
 * console draw the same thread, and a second list of buttons written somewhere
 * else is how they come to disagree about what an offer is. `answer` is a word
 * about the conversation rather than about the button, so a caller wiring it up
 * is not reading a label to decide what happened.
 *
 * A kind that is not here draws its words and nothing else -- see `saying`.
 */
const KINDS = {
  offer: ANSWERS,
  mail_match: [
    { answer: "run", label: "Run it", quiet: false },
    { answer: "no", label: "Not now", quiet: true },
  ],
  nudge: [
    { answer: "do", label: "Do it", quiet: false },
    { answer: "not-here", label: "Not for this page", quiet: true },
  ],
  result: [
    { answer: "undo", label: "Undo that", quiet: false },
    { answer: "wrong", label: "It\u2019s wrong \u2014 I\u2019ll fix it", quiet: true },
  ],
};

/** A failure says the one thing that would help, and the backend chooses which.
 *
 * One button, never three. A failure is read by somebody who wants it to stop
 * being a failure, and a row of options is a decision handed back to the person
 * least able to make it.
 */
const NEXT = {
  retry: "Try another way",
  ask: "Ask me",
  open: "Open the page",
};

/** A thread as DOM: what was said, oldest first, and the box to say more in.
 *
 * `onSay(text)` is called with a non-empty sentence the operator typed.
 * `onPress(answer, message, where)` is called when an offer is answered --
 * `where` is the list item that offer was drawn in, so a caller can say
 * something back on the offer itself rather than into nothing.
 *
 * Both are optional, because the shape of a thread is worth asserting on
 * without wiring a worker up to it.
 */
export function ledger(thread, local = {}, { onPress, runs } = {}) {
  const root = document.createElement("div");
  root.className = "thread";

  const said = document.createElement("ul");
  said.className = "said";
  const messages = thread?.messages || [];
  const spent = alreadyAnswered(messages);
  const offers = local?.offers || [];

  // The server's thread and what only this browser knows, in one order. A nudge
  // is never written down -- it lives about ninety seconds, and a conversation
  // full of them is noise -- but the operator reads one place, and things that
  // happened belong in the order they happened.
  const entries = [
    ...messages.map((message) => ({ at: message.said_at, message })),
    ...(local?.nudges || []).map((nudge) => ({ at: nudge.at, nudge })),
  ].sort((a, b) => String(a.at || "").localeCompare(String(b.at || "")));

  let lastMinute = "";
  for (const entry of entries) {
    const item = entry.message
      ? saying(entry.message, onPress, spent, { offers, runs })
      : nudging(entry.nudge, onPress);
    const minute = hhmm(entry.at);
    // One cell per entry, filled only when the minute changes. Repeating 12:04
    // against three things said in the same minute is noise exactly where the
    // eye is looking for structure.
    const when = document.createElement("time");
    when.className = "when";
    when.textContent = minute === lastMinute ? "" : minute;
    if (minute) lastMinute = minute;
    item.prepend(when);
    said.append(item);
  }
  root.append(said);

  return root;
}

/** Local time, because the operator reads it against their own day. */
function hhmm(at) {
  const when = new Date(at);
  if (Number.isNaN(when.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(when.getHours())}:${pad(when.getMinutes())}`;
}

/** One message. Three speakers, three shapes -- the shape is `data-speaker`,
 * which is a hook for the stylesheet rather than three near-identical builders
 * here. */
/** Which offers have already been answered, by the candidate they were about.
 *
 * Named for what it returns rather than `answered`, which panel.js already uses
 * for the act of answering one. They are module-scoped and never collide in the
 * browser, but two functions of that name in adjacent files meaning opposite
 * halves of the same exchange is a trap for whoever reads them next.
 *
 * An offer is a record of something that was said, so it is never edited to
 * report its own answer -- the answer is its own message. But an offer whose
 * answer is further down the thread must stop carrying live buttons: pressing
 * one is refused by the backend ("this candidate is already taught"), which is
 * safe and useless. The operator asked; the thread should look like it.
 */
export function alreadyAnswered(messages) {
  const done = new Map();
  for (const message of messages) {
    const decision = message.decision;
    if (decision?.kind === "answered" && decision.candidate_id) {
      done.set(decision.candidate_id, decision.answer || "answered");
    }
  }
  return done;
}

function nudging(nudge, onPress) {
  if (nudge.source === "rig" && nudge.state === "open") return offeringToFinish(nudge, onPress);
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "nudge";
  item.dataset.state = nudge.state || "open";
  if (nudge.id) item.dataset.id = nudge.id;

  const what = document.createElement("p");
  what.className = "what";
  what.textContent =
    nudge.state === "by-hand"
      ? `${nudge.title} \u2014 you did it yourself`
      : nudge.state === "open"
        ? `${nudge.title} \u2014 you have done this here before`
        : `You were on ${nudge.title}`;
  item.append(what);

  // Only while it is still asking. A nudge ends three ways and two of them are
  // not answers -- they did the task themselves, or they went somewhere else --
  // and a prompt still offering to do a task already done is the failure the
  // ninety-second life exists to avoid.
  if (nudge.state === "open") {
    item.append(pressing(KINDS.nudge, nudge, item, onPress));
  }
  return item;
}

/** The rig's own offer: what it read, what it still needs, and the two answers.
 *
 * A backend nudge says "you have done this here before" and offers to do the
 * next one. This one is about the job in front of somebody right now -- half
 * typed, or just arrived at -- so it says back what it read off the page, asks
 * for the rest, and offers to finish. The fields are the reason it is an offer
 * and not a run: nothing starts until every blank the job needs has something
 * in it, because a run that stops at the first empty box is worse than never
 * having offered.
 *
 * Its Yes is `start-rig-run` and its No is `drop-nudge`, both distinct from the
 * `nudge-answer` a backend nudge sends. The worker reports one fate per path,
 * and an offer that reported two is one the rig cannot count.
 */
function offeringToFinish(nudge, onPress) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "nudge";
  item.dataset.state = "open";
  item.dataset.id = nudge.id;

  const typed = Object.values(nudge.values || {}).join(", ");
  const what = document.createElement("p");
  what.className = "what";
  what.textContent =
    nudge.k > 0
      ? `${nudge.title} \u2014 ${typed}, so far. Want me to finish it?`
      : `${nudge.title} \u2014 want me to do it?`;
  item.append(what);

  const fields = new Map();
  for (const name of nudge.missing || []) {
    const field = document.createElement("input");
    field.type = "text";
    field.placeholder = name;
    fields.set(name, field);
    item.append(field);
  }

  const yes = document.createElement("button");
  yes.type = "button";
  yes.textContent = nudge.k > 0 ? "Yes, finish it" : "Yes, do it";
  const no = document.createElement("button");
  no.type = "button";
  no.className = "quiet";
  no.textContent = "No thanks";

  // Blank is blank after trimming: a field of spaces is not an answer to a
  // question the run is going to ask the system on the other side.
  const ready = () => [...fields.values()].every((field) => String(field.value || "").trim());
  // One press ends the card. The ledger does not redraw when an offer is
  // answered, so without this the buttons of a refused offer are still live
  // under the operator's cursor -- and "No thanks" then "Yes" is a run started
  // on an offer already reported dismissed, which is two fates for one offer.
  // The worker refuses that as well; this is the half that keeps the panel from
  // ever asking.
  let ended = false;
  const settle = () => {
    yes.disabled = ended || !ready();
    no.disabled = ended;
  };
  settle();
  for (const field of fields.values()) field.addEventListener("input", settle);
  yes.addEventListener("click", () => {
    if (ended) return;
    const values = Object.fromEntries(
      [...fields].map(([name, field]) => [name, String(field.value || "").trim()]),
    );
    ended = true;
    settle();
    onPress?.("start-rig-run", nudge, item, yes, { values });
  });
  no.addEventListener("click", () => {
    if (ended) return;
    ended = true;
    settle();
    onPress?.("drop-nudge", nudge, item, no);
  });

  const row = document.createElement("div");
  row.className = "row";
  row.append(yes, no);
  item.append(row);
  return item;
}

function saying(message, onPress, spent = new Map(), { offers = [], runs } = {}) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = message.speaker || "system";
  if (message.id) item.dataset.id = message.id;

  const what = document.createElement("p");
  what.className = "what";
  // The one line this whole file is about. Never `innerHTML`.
  what.textContent = message.text || "";
  item.append(what);

  // A decision this panel knows how to answer gets the buttons for answering
  // it. Any other kind -- one a newer backend reached and this copy of the
  // extension has never heard of -- renders the words and nothing else. A
  // panel that blanked, or threw, on an unfamiliar `kind` would mean a backend
  // could not add one without every browser in the field going dark first.
  const kind = message.decision?.kind;
  if (kind) item.dataset.kind = kind;

  if (kind === "offer") {
    const already = spent.get(message.decision.candidate_id);
    // Answered further down the thread: the words stay, the buttons go. The
    // offer is still what was said, and the answer is still its own message;
    // what is gone is the invitation to answer a second time.
    if (already) item.dataset.answered = already;
    else item.append(pressing(KINDS.offer, message, item, onPress));
  } else if (kind === "mail_match") {
    matched(item, message, offers, onPress);
  } else if (kind === "question") {
    asking(item, message, onPress);
  } else if (kind === "failure") {
    const label = NEXT[message.decision.next];
    if (label) {
      item.append(
        pressing([{ answer: message.decision.next, label, quiet: false }], message, item, onPress),
      );
    }
  } else if (kind === "result") {
    item.append(pressing(KINDS.result, message, item, onPress));
  } else if (kind === "run" && runs) {
    const live = runs.get?.(message.decision.run_id);
    if (live) item.append(live);
  }
  return item;
}

/** A row of presses, built from the table above.
 *
 * `values` reaches `onPress` last and is undefined for everything but a matched
 * mail, where the operator may have changed a field before pressing. A caller
 * that does not care never reads it.
 */
function pressing(answers, subject, item, onPress, values) {
  const row = document.createElement("div");
  row.className = "row";
  for (const { answer, label, quiet } of answers) {
    const button = document.createElement("button");
    button.type = "button";
    if (quiet) button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", () =>
      onPress?.(answer, subject, item, button, values?.()),
    );
    row.append(button);
  }
  return row;
}

/** A mail that matched a task: why, and what it would run with.
 *
 * The values are the browser's, never the thread's. What a watch read out of
 * somebody's mail is not written down -- the message carries which names were
 * read, and the offer beside it carries what they said. When that offer is gone
 * the card says so rather than drawing empty boxes and pretending a press would
 * work.
 *
 * What it says instead of the sender and the subject: the terms the operator
 * pointed this watch at, and the host it matched on. `watch.js` is explicit
 * that no sender, subject or body ever leaves the frame that read the mail --
 * an offer is held in `chrome.storage`, which is disk, so carrying them here to
 * put on a card would be writing down exactly what that rule exists to keep
 * unwritten. The terms are the operator's own words and already stored, and
 * they are the better answer anyway: they say why this matched.
 */
function matched(item, message, offers, onPress) {
  const decision = message.decision || {};
  const offer = offers.find((each) => each.id === decision.offer_id);
  if (!offer) {
    const note = document.createElement("p");
    note.className = "note";
    note.textContent =
      "The mail this matched is no longer held in this browser. Open it again to run it.";
    item.append(note);
    return;
  }

  const why = document.createElement("p");
  why.className = "note";
  const because = (offer.terms || [])
    .map((term) => `${term.field} contains \u201c${term.contains}\u201d`)
    .join(" and ");
  why.textContent = because
    ? `Recognised in ${offer.host}: ${because}`
    : `Recognised in ${offer.host}`;
  item.append(why);

  // Every value a field, whether the mail said it or not. The ones it did not
  // say are the reason a match is offered rather than run: somebody has to
  // supply them, and the moment to do that is before the run starts.
  const fields = new Map();
  const names = [
    ...Object.keys(offer.values || {}),
    ...(offer.missing || []).filter((name) => !(name in (offer.values || {}))),
  ];
  for (const name of names) {
    const field = document.createElement("input");
    field.type = "text";
    field.placeholder = name;
    field.value = (offer.values || {})[name] ?? "";
    fields.set(name, field);
    item.append(field);
  }

  item.append(
    pressing(KINDS.mail_match, message, item, onPress, () =>
      Object.fromEntries([...fields].map(([name, field]) => [name, field.value])),
    ),
  );
}

/** A run stopped and needs somebody to decide.
 *
 * The choices it knows, and a box for one it does not. A question with only
 * buttons is a question that cannot be answered when the right answer is not
 * among them, which is the case that made somebody stop and ask.
 */
function asking(item, message, onPress) {
  const decision = message.decision || {};
  const row = document.createElement("div");
  row.className = "row";
  for (const choice of decision.choices || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = choice;
    button.addEventListener("click", () => onPress?.(`choice:${choice}`, message, item, button));
    row.append(button);
  }
  item.append(row);

  const typed = document.createElement("input");
  typed.type = "text";
  typed.placeholder = "or type an answer";
  typed.addEventListener("keydown", (event) => {
    const value = String(typed.value || "").trim();
    if (event.key === "Enter" && value) onPress?.(`choice:${value}`, message, item, typed);
  });
  item.append(typed);
}

/** The box at the bottom.
 *
 * Cleared on send and not refilled with what was sent: the server answers a
 * post with the whole thread, so what the operator typed comes back as a
 * message in the ledger. A panel that also appended it locally would be
 * guessing at what the server recorded, and would show it twice when the guess
 * happened to be right.
 */
/** The box somebody types into, built apart from the messages.
 *
 * Its own export because the panel pins it to the bottom of the frame rather
 * than putting it after the last message: a long conversation would otherwise
 * push the one control that must always be reachable off the bottom.
 */
export function composer(onSay) {
  const row = document.createElement("div");
  row.className = "row composer";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = ASKING;

  const send = document.createElement("button");
  send.type = "button";
  send.textContent = "Send";

  const say = () => {
    const text = String(input.value || "").trim();
    if (!text) return;
    input.value = "";
    onSay?.(text);
  };
  send.addEventListener("click", say);
  // Enter, because this is a chat box and nobody reaches for the mouse in one.
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") say();
  });

  row.append(input, send);
  return row;
}
