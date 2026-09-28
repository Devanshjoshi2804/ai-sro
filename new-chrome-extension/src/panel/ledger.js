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
  mail_draft: [
    { answer: "send-draft", label: "Send it", quiet: false },
    {
      answer: "drop-draft",
      label: "No, I\u2019ll ask them myself",
      quiet: true,
    },
  ],
  result: [
    { answer: "undo", label: "Undo that", quiet: false },
    {
      answer: "wrong",
      label: "It\u2019s wrong \u2014 I\u2019ll fix it",
      quiet: true,
    },
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

// The one thing this file reaches for. It has been import-free -- everything
// it needs is either handed to it or built here -- and a lookup's answer is
// the exception worth making: five states with a table in one of them is its
// own module, and inlining it here would put a row-shape heuristic in the
// middle of a thread renderer.
import { result } from "./result.js";

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
  // Loud here rather than silent on the press. A caller once handed this a
  // string -- a local in `show()` shadowed the handler of the same name -- and
  // every button in the thread threw "onPress is not a function" into a click
  // listener nobody was watching: the panel drew cards, the operator pressed
  // them, and nothing happened, for thirteen minutes, twice.
  if (onPress !== undefined && typeof onPress !== "function") {
    throw new TypeError(
      "ledger was given something to press with that cannot be called",
    );
  }
  const root = document.createElement("div");
  root.className = "thread";

  const said = document.createElement("ul");
  said.className = "said";
  const messages = thread?.messages || [];
  const spent = alreadyAnswered(messages);
  const offers = local?.offers || [];

  // The server's thread and what only this browser knows, in one order: the
  // operator reads one place, and things that happened belong in the order
  // they happened.
  const entries = [
    // Not the mining candidates. This deployment runs the rig: a job it has
    // mined is asked about in the conversation by the backend, and the older
    // pipeline's "you've done this 4 times, want me to do the next one?" is an
    // offer to teach a SKILL from recordings, which is not the system this
    // browser drives any more. An operator pressed one and got "the doings
    // differ too much", for work the rig already holds as a seven-step job.
    //
    // Dropped where it is read rather than where it is written: the backend
    // goes on mining candidates and the console goes on reviewing them. What
    // ends here is offering them to the person at the warehouse.
    ...messages
      .filter((message) => message.decision?.kind !== "offer")
      .map((message) => ({ at: message.said_at, message })),
    ...(local?.answer
      ? [{ at: at(local.answer.askedAt), answer: local.answer }]
      : []),
    ...(local?.nearMisses || []).map((miss) => ({ at: at(miss.at), miss })),
    ...(local?.waiting || []).map((card) => ({
      at: card.asked_at,
      waiting: card,
    })),
    // The sentence that has been sent and not yet answered. Last, whatever the
    // clock says: it is the most recent thing that happened by definition, and
    // a locally-stamped time can lose a race with the server's own.
    ...(local?.sending ? [{ at: "\uffff", sending: local.sending }] : []),
    // And the mail that has gone out and not been answered. After everything
    // said, for the sending entry's reason: it is true right now, and it goes
    // on being true across however many polls it takes.
    ...(local?.mail?.awaiting ? [{ at: "\ufffe", awaiting: local.mail }] : []),
  ].sort((a, b) => String(a.at || "").localeCompare(String(b.at || "")));

  let lastMinute = "";
  for (const entry of entries) {
    const item = entry.message
      ? saying(entry.message, onPress, spent, {
          offers,
          runs,
          here: local?.here || "",
        })
      : entry.answer
        ? answering(entry.answer)
        : entry.miss
          ? nearlyFired(entry.miss)
          : entry.waiting
            ? waitingOnYou(entry.waiting, onPress)
            : entry.sending
              ? sending(entry.sending)
              : waitingOnAMailbox(entry.awaiting);
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

/** What was just said, and the fact that an answer is being worked out.
 *
 * Two elements rather than one, because they are two different claims: the
 * operator's own words, which are certain, and a mark that something is
 * happening, which is all this browser can honestly say about the reply.
 *
 * Both are replaced the moment the server answers -- nothing here is kept, and
 * nothing here is a statement about what was decided.
 */
function sending({ text }) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "operator";
  item.dataset.state = "sending";
  const what = document.createElement("p");
  what.className = "what";
  what.textContent = text;
  item.append(what);

  const thinking = document.createElement("p");
  thinking.className = "detail thinking";
  thinking.dataset.kind = "thinking";
  // Three dots the stylesheet animates, and the word beside them for anybody
  // whose browser is not animating anything -- a bare "..." that never moves
  // is indistinguishable from a message somebody actually sent.
  thinking.textContent = "thinking";
  const dots = document.createElement("span");
  dots.className = "dots";
  dots.textContent = "\u2026";
  thinking.append(dots);
  item.append(thinking);
  return item;
}

/** The mail that has gone and the answer that has not come.
 *
 * A mail leaves over the operator's name and the reply arrives by a poll they
 * cannot see. What that looked like was one sentence -- "I will carry on when
 * they reply" -- and then, for as long as it took, a panel doing nothing at
 * all. Somebody watching it has no way to tell a system that is checking every
 * two minutes from one that forgot.
 *
 * So the wait is drawn as what it is, continuously: who is being waited on,
 * when the mailbox was last read, and -- while a read is actually out -- that
 * one is happening this second. Nothing here is an estimate: every number is
 * something this browser did.
 */
export function waitingOnAMailbox(mail, now = Date.now()) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "awaiting-mail";
  if (mail.looking) item.dataset.state = "looking";

  const what = document.createElement("p");
  what.className = "what";
  what.textContent = `Waiting for ${mail.awaiting?.to || "a reply"}.`;
  item.append(what);

  const how = document.createElement("p");
  how.className = "detail thinking";
  how.dataset.kind = "looking";
  // The words say which of the two states this is, because the animation is
  // the part a stylesheet can decline to run -- and a line that reads the same
  // whether or not anything is happening is the line this replaces.
  how.textContent = mail.looking
    ? "reading the mailbox"
    : `asked ${_ago(mail.awaiting?.at, now)} \u00b7 last read ${_ago(mail.lookedAt, now)}`;
  if (mail.looking) {
    const dots = document.createElement("span");
    dots.className = "dots";
    dots.textContent = "\u2026";
    how.append(dots);
  }
  item.append(how);
  return item;
}

/** How long ago, in the roundest words that are still true.
 *
 * Never "0 seconds ago" and never a date: what this is for is a person judging
 * whether a thing is still happening, and past an hour the answer is the same
 * whatever the number says.
 */
function _ago(at, now = Date.now()) {
  const was = Number(at) || 0;
  if (!was) return "not yet";
  const seconds = Math.max(0, Math.round((now - was) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes}m ago` : `${Math.round(minutes / 60)}h ago`;
}

/** A rule that almost fired, said out loud.
 *
 * The quietest failure this panel has: a mail arrived, the operator's rule was
 * about that conversation, and nothing happened -- and until this line existed
 * the only way to find out was to notice that nothing had.
 *
 * It offers nothing to press. The rule did not match, and a button that ran it
 * anyway would be this panel deciding the operator's words meant something
 * they did not write. What it gives them is the term they wrote, so they can
 * widen it themselves.
 */
function nearlyFired(miss) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "near-miss";

  const what = document.createElement("p");
  what.className = "what";
  // The operator's own words, which is all this browser was ever told. Nothing
  // of the mail reaches here -- see `watch.js`'s `nearly`.
  what.textContent = `A mail nearly matched "${(miss.terms || []).join('", "')}" \u2014 close, but not what you wrote.`;
  item.append(what);
  return item;
}

/** A millisecond clock as the ISO string everything else in the order uses. */
function at(millis) {
  return millis ? new Date(millis).toISOString() : "";
}

/** What was asked of the systems, and what each of them said back.
 *
 * No press on it, deliberately. A read writes nothing, so it has already
 * happened by the time this is drawn -- a card saying "shall I go and look?"
 * would be a question about a question. What it offers instead is the reason:
 * every line names the system and the thing that was read, because an answer
 * whose source cannot be seen is one nobody can check.
 *
 * The one case with nothing to show is the one worth showing most: a question
 * this deployment has already written down as ambiguous stops before it asks
 * anybody, and the card says which word and which options rather than a number
 * that would be a guess.
 */
function answering(answer) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "answer";

  const asked = document.createElement("p");
  asked.className = "what";
  asked.textContent = answer.question || answer.said || "";
  item.append(asked);

  if (answer.asks) {
    const stopped = document.createElement("p");
    stopped.className = "detail";
    stopped.textContent = `${answer.asks.question} — ${(answer.asks.options || []).join(" or ")}`;
    item.append(stopped);
    return item;
  }

  if (answer.refused) {
    const why = document.createElement("p");
    why.className = "detail";
    why.textContent = answer.refused;
    item.append(why);
    return item;
  }

  const found = document.createElement("ul");
  found.className = "answers";
  for (const one of answer.answers || []) {
    const line = document.createElement("li");
    line.dataset.ok = String(Boolean(one.ok));
    // What came back, read rather than previewed. This was 240 characters of
    // raw JSON per system -- `{"data":[{"supplierNumber":"100012","supplier`
    // -- which answers "how many suppliers are at SG" with a person counting
    // nothing. `result.js` has the five ends a lookup has and the count first.
    line.append(result(one));
    found.append(line);
  }
  item.append(found);
  return item;
}

/** One lookup's answer, short enough to read in a column. */
/** A rule that fired and stopped to ask.
 *
 * The card an operator could not see. A page rule went off on the page in
 * front of them, the fire became a confirmation, and the confirmation was
 * drawn in the console -- another tab, which from where they were standing is
 * indistinguishable from nothing having happened. They said so, in those
 * words: "I just logged in, nothing on panel".
 *
 * Answered from here as well as there. Either window may answer it and the
 * backend settles which was first, so the two cannot disagree about what was
 * decided -- only about how quickly they notice.
 */
export function waitingOnYou(card, onPress) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "waiting";
  item.dataset.id = card.id;

  const what = document.createElement("p");
  what.className = "what";
  what.textContent = `${card.skill_name} \u2014 ${card.because}. Shall I?`;
  item.append(what);

  const typed = Object.entries(card.values || {});
  if (typed.length) {
    // What it would run with, before it runs: the one moment somebody can read
    // a write's values and still stop it.
    //
    // Behind a disclosure rather than in front of the buttons. Twelve values
    // in a 360-pixel column push the two controls this card exists for below
    // the fold, and a person who cannot see the buttons cannot answer -- but a
    // write whose values are unreadable is one nobody should be answering
    // either. `<details>` is the platform's answer to exactly that and costs
    // no script: shut by default, one press to read, and the browser handles
    // the keyboard and the screen reader.
    const shown = document.createElement("details");
    shown.className = "request";
    const summary = document.createElement("summary");
    summary.textContent = `what it would use (${typed.length})`;
    const said = document.createElement("p");
    said.className = "detail";
    said.textContent = typed
      .map(([name, value]) => `${name}: ${value}`)
      .join(" \u00b7 ");
    shown.append(summary, said);
    item.append(shown);
  }

  const yes = document.createElement("button");
  yes.type = "button";
  yes.textContent = "Yes, do it";
  const no = document.createElement("button");
  no.type = "button";
  no.className = "quiet";
  no.textContent = "No";
  let ended = false;
  const settle = () => {
    yes.disabled = ended;
    no.disabled = ended;
  };
  // One answer, however it arrives -- the press and the key are the same
  // decision and must not be two paths that can both be taken.
  const answer = (which, button) => {
    if (ended) return;
    ended = true;
    settle();
    onPress?.(which, card, item, button);
  };
  yes.addEventListener("click", () => answer("waiting-approve", yes));
  no.addEventListener("click", () => answer("waiting-decline", no));

  item.append(actions(yes, no));
  // The keys, while this card has the focus.
  //
  // Not on the document. A panel that took Esc globally would throw away what
  // somebody was typing in the composer, and one that took Cmd-Enter globally
  // would approve a write while they were reading something else -- the
  // shortcut for a decision has to belong to the thing being decided.
  item.addEventListener("keydown", (event) => {
    if (ended) return;
    if (event.key === "Escape") answer("waiting-decline", no);
    else if (event.key === "Enter" && (event.metaKey || event.ctrlKey))
      answer("waiting-approve", yes);
  });
  return item;
}

/** The band under a card that is asking for a decision.
 *
 * The primary press last, on the right, which is where every platform this
 * panel sits beside puts it -- and the way out first, because a person who has
 * decided against something should not have to read past the button that does
 * it. The keys are named ON the buttons rather than in a line of prose nobody
 * reads twice.
 */
function actions(yes, no) {
  const row = document.createElement("div");
  row.className = "row actions";
  hint(no, "Esc");
  // `typeof` because this file is built and tested without a browser around
  // it, and a panel that threw here would draw no card rather than the wrong
  // symbol on one.
  const mac =
    typeof navigator !== "undefined" &&
    /mac/i.test(navigator.platform || navigator.userAgent || "");
  hint(yes, mac ? "\u2318\u23ce" : "Ctrl \u23ce");
  row.append(no, yes);
  return row;
}

/** Name the key on the button it presses. */
function hint(button, keys) {
  const said = document.createElement("kbd");
  said.textContent = keys;
  button.append(said);
}

/** Whether this offer is about somewhere the operator is not.
 *
 * Host and not page: an offer is about a task on a system, and an operator who
 * is anywhere on that system can sensibly say yes. Unknown either way -- an
 * older backend that sent no host, a panel that has not learned which tab it
 * is docked beside -- keeps the buttons, because hiding a control on a guess
 * is worse than showing one that turns out to be about the next tab.
 */
function elsewhere(message, here) {
  const host = message.decision?.host;
  return Boolean(host && here && host !== here);
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
    // A mail that went. By the run where there is one -- what must not be
    // offered twice is asking one person about one request -- and by the draft
    // itself where there is not. A card asks before any run exists, so keyed
    // only on the run this claimed nothing, and `Send it` stayed live under a
    // mail already sitting in somebody's inbox.
    if (decision?.kind === "mail_sent") {
      if (decision.run_id) done.set(decision.run_id, "sent");
      if (decision.draft_id) done.set(decision.draft_id, "sent");
    }
  }
  return done;
}

function saying(
  message,
  onPress,
  spent = new Map(),
  { offers = [], runs, here = "" } = {},
) {
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

  // What a lookup came back with, drawn the way the answer card draws it.
  //
  // The conversation used to carry the SCREEN WALK for a question -- "Nobody
  // has demonstrated reading that, so I will work it out on the screen" --
  // while the answer itself arrived through `/v1/ask` into a card beside it.
  // Now the door that owns a question answers into the thread, and `result()`
  // is what makes fifty records readable: a count and the first few in a
  // table, rather than 240 characters of raw JSON that never reach the row
  // somebody asked about.
  if (kind === "looked") {
    const found = document.createElement("ul");
    found.className = "answers";
    for (const one of message.decision.answers || []) {
      const line = document.createElement("li");
      line.dataset.ok = String(Boolean(one.ok));
      const drawn = result(one);
      if (drawn) line.append(drawn);
      found.append(line);
    }
    item.append(found);
    return item;
  }

  if (kind === "offer") {
    const already = spent.get(message.decision.candidate_id);
    // Answered further down the thread: the words stay, the buttons go. The
    // offer is still what was said, and the answer is still its own message;
    // what is gone is the invitation to answer a second time.
    if (already) item.dataset.answered = already;
    else if (elsewhere(message, here)) {
      // Somewhere else entirely. An operator standing on their login page was
      // shown "create an equipment type -- want me to do the next one?" with
      // live buttons, for a warehouse host they were not on: pressing it would
      // drive a tab they are not looking at, off evidence from hours ago. The
      // sentence stays, because it was said; the invitation does not, because
      // it is not an invitation from here.
      item.dataset.answered = "elsewhere";
      const where = document.createElement("p");
      where.className = "detail";
      where.textContent = `on ${message.decision.host}`;
      item.append(where);
    } else item.append(pressing(KINDS.offer, message, item, onPress));
  } else if (kind === "mail_match") {
    matched(item, message, offers, onPress);
  } else if (kind === "which_job") {
    // Two jobs it could have meant, and a person says which.
    //
    // Nothing here starts anything: the press says the job's own name back
    // into the conversation, and the door reads that sentence with no
    // ambiguity left in it. A button that started a run off a reading that
    // had already said it was unsure would be the guess this question exists
    // to avoid, wearing a confirmation.
    const choosing = document.createElement("div");
    choosing.className = "row";
    for (const title of message.decision.titles || []) {
      const one = document.createElement("button");
      one.type = "button";
      one.textContent = title;
      one.addEventListener("click", () =>
        onPress?.("which-job", message, item, one, { title }),
      );
      choosing.append(one);
    }
    item.append(choosing);
  } else if (kind === "job" && message.decision.confirm) {
    // A request the server would not run by itself -- the operator's mail to
    // somebody else, or one on a thread that already ran. The press says the
    // answer into the conversation, and the door's yes is a press's start.
    const choosing = document.createElement("div");
    choosing.className = "row";
    for (const [label, said] of [
      ["Do it", "yes"],
      ["Leave it", "no"],
    ]) {
      const one = document.createElement("button");
      one.type = "button";
      one.textContent = label;
      one.addEventListener("click", () =>
        onPress?.("say", message, item, one, { said, answering: message.id }),
      );
      choosing.append(one);
    }
    item.append(choosing);
  } else if (kind === "question") {
    asking(item, message, onPress);
  } else if (kind === "failure") {
    const label = NEXT[message.decision.next];
    if (label) {
      item.append(
        pressing(
          [{ answer: message.decision.next, label, quiet: false }],
          message,
          item,
          onPress,
        ),
      );
    }
  } else if (kind === "mail_draft") {
    // The mail, whole, before anything can send it.
    //
    // This is the one thing this system writes that leaves the company, over
    // the operator's name, to somebody outside every system here -- and it
    // cannot be unsent. The press is the authorisation and an authorisation
    // given without reading is not one, so the words are on the card rather
    // than behind a disclosure: nobody expands a `<details>` before pressing a
    // button they have already decided about.
    //
    // Already sent is not a thing to offer again. `mail_sent` further down the
    // thread is the answer to this one.
    if (
      spent.get(message.decision.run_id) !== "sent" &&
      spent.get(message.id) !== "sent"
    ) {
      // Who and what, on their own lines. A mail is read as a mail -- the
      // recipient, then the subject, then the words -- and one run-on line is
      // the shape of a log entry, not of something somebody is authorising.
      const to = document.createElement("p");
      to.className = "detail";
      to.textContent = `To ${message.decision.to}`;
      item.append(to);

      const subject = document.createElement("p");
      subject.className = "detail subject";
      subject.textContent = message.decision.subject || "";
      item.append(subject);

      const body = document.createElement("pre");
      body.className = "draft";
      // `textContent` on a `<pre>`: the mail is plain text, its line breaks
      // are the shape somebody reads it in, and nothing in it is markup.
      body.textContent = String(message.decision.body || "");
      item.append(body);
      item.append(pressing(KINDS.mail_draft, message, item, onPress));
    } else item.dataset.answered = "sent";
  } else if (kind === "result") {
    item.append(pressing(KINDS.result, message, item, onPress));
  } else if ((kind === "run" || kind === "job") && runs) {
    // `run`, and the `job` a yes became: the backend starts that run itself
    // and names it on the message that says so.
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
      Object.fromEntries(
        [...fields].map(([name, field]) => [name, field.value]),
      ),
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
    button.addEventListener("click", () =>
      onPress?.(`choice:${choice}`, message, item, button),
    );
    row.append(button);
  }
  item.append(row);

  const typed = document.createElement("input");
  typed.type = "text";
  typed.placeholder = "or type an answer";
  typed.addEventListener("keydown", (event) => {
    const value = String(typed.value || "").trim();
    if (event.key === "Enter" && value)
      onPress?.(`choice:${value}`, message, item, typed);
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
  // The box is the control, and the control lives inside it.
  //
  // It was an input with a Send button beside it, which spends a third of a
  // 360-pixel row on a word for something the Enter key already does -- and
  // reads as a form rather than as somewhere to say something. So the border
  // moves to the box, the field inside it is bare, and the one press that is
  // not the Enter key sits in the corner of it as an arrow.
  //
  // One composer, and it is always there. It used to be hidden on Home, so an
  // operator who thought of something while looking at their cards had to find
  // the other tab before they could say it -- and now that questions from a
  // run arrive in the conversation, the box they answer in must be under their
  // hand wherever they are standing.
  const row = document.createElement("div");
  row.className = "composer";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = ASKING;

  const tools = document.createElement("div");
  tools.className = "tools";

  const send = document.createElement("button");
  send.type = "button";
  send.className = "send";
  // An arrow, and a name for anything that cannot see it. The word "Send" was
  // the button; now the shape is, and a screen reader must still be told what
  // it does.
  send.textContent = "\u2191";
  send.setAttribute("aria-label", "Send");

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

  tools.append(send);
  row.append(input, tools);
  return row;
}
