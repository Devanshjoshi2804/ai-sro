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
// what `transcript.test.mjs` does.

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
  { answer: "no", label: "No thanks", quiet: true },
];

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
export function transcript(thread, { onSay, onPress } = {}) {
  const root = document.createElement("div");
  root.className = "thread";

  const said = document.createElement("ul");
  said.className = "said";
  const messages = thread?.messages || [];
  const spent = alreadyAnswered(messages);
  for (const message of messages) said.append(saying(message, onPress, spent));
  root.append(said);

  root.append(composer(onSay));
  return root;
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
function alreadyAnswered(messages) {
  const done = new Map();
  for (const message of messages) {
    const decision = message.decision;
    if (decision?.kind === "answered" && decision.candidate_id) {
      done.set(decision.candidate_id, decision.answer || "answered");
    }
  }
  return done;
}

function saying(message, onPress, spent = new Map()) {
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
  if (message.decision?.kind === "offer") {
    const already = spent.get(message.decision.candidate_id);
    // Answered further down the thread: the words stay, the buttons go. The
    // offer is still what was said, and the answer is still its own message;
    // what is gone is the invitation to answer a second time.
    if (already) item.dataset.answered = already;
    else item.append(answers(message, item, onPress));
  }
  return item;
}

function answers(message, item, onPress) {
  const row = document.createElement("div");
  row.className = "row";
  for (const { answer, label, quiet } of ANSWERS) {
    const button = document.createElement("button");
    button.type = "button";
    if (quiet) button.className = "quiet";
    button.textContent = label;
    button.addEventListener("click", () => onPress?.(answer, message, item, button));
    row.append(button);
  }
  return row;
}

/** The box at the bottom.
 *
 * Cleared on send and not refilled with what was sent: the server answers a
 * post with the whole thread, so what the operator typed comes back as a
 * message in the transcript. A panel that also appended it locally would be
 * guessing at what the server recorded, and would show it twice when the guess
 * happened to be right.
 */
function composer(onSay) {
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
