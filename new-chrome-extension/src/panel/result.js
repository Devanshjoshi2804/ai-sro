// What one lookup came back with, as something a person can read.
//
// **Nothing here decides what a record is.** It used to, and that was the
// whole fault: the lookup plane handed the raw body across, so this file
// parsed JSON, hunted for the rows, picked columns and counted them -- and so
// did the console, and so did anything else that drew an answer. Three
// guesses at one question, and this one guessed badly. Measured on the
// deployment 2026-09-21, beside the warehouse's own screen: the WMS grid
// showed `Customer Type | Description`, and this drew
//
//     URNFORMAT  ABSOLUTEGROUP  ALLOCATIONSEARCHPATH  ALLOWSOURCE…  BULKPI…
//         —            —                 —                 —          false
//
// the first six KEYS of a payload that alphabetises.
//
// `application/execution/answer.py` had already decided all of it, for every
// other read in this system: a column earns its place by carrying a value,
// the ranking puts code, name and description first, a `self_uri` is dropped
// as a link, two columns holding one value are one, the count is the system's
// own total rather than the page length, and `sentence()` says it in a line.
// The lookup plane now reads through it too, so this file draws a structure.
//
// Five states, because a lookup has five ends and four of them are not rows:
//
//   1. The system refused        -- status and what it said.
//   2. An ERROR body             -- its own words, which are better than ours.
//   3. Records                   -- the sentence, then the count, then a table.
//   4. Answered, not records     -- one record, a number, a page: as it came.
//   5. Nothing to show           -- a screen, whose picture stays server-side.
//
// **The count is not the product any more; the SENTENCE is.** Somebody asking
// "is there a customer type called KKYT" has been answered by a line, and the
// table is what they check it against.
//
// Pure, and given the answer rather than fetching it.

/** How many rows this panel shows. Eight is what fits beside a warehouse
 * screen without the card becoming the screen. */
export const K_ROWS = 8;

/** How much of one cell. Long enough for a description, short enough that one
 * fat field cannot push every other column off the panel. */
export const K_CELL = 40;

/** How much of a result a word may pick out and still be said to name
 * something. A quarter: past that it is describing the collection rather than
 * choosing within it. */
export const K_TELLING = 0.25;

/**
 * The card, or `null` when there is nothing to say at all.
 *
 * `open` is whether this is the turn somebody is looking at. An older answer
 * collapses to its count, because a conversation with four tables in it is a
 * conversation nobody scrolls.
 *
 * `asked` is the question, and it is used for one thing: putting the record
 * somebody named at the top. The reader cannot do that -- it is handed a body
 * and never the question -- and it is the only judgement left on this side.
 */
export function result(looked, { open = true, onOpen, asked = "" } = {}) {
  if (!looked) return null;
  const box = document.createElement("div");
  box.className = "result";
  box.dataset.ok = String(Boolean(looked.ok));

  const where = document.createElement("p");
  where.className = "where";
  where.textContent = `${looked.system || ""} · ${looked.target || ""}`.trim();
  box.append(where);

  if (!looked.ok) {
    box.append(
      _line(
        "detail",
        looked.detail || `answered ${looked.status ?? ""}`.trim(),
      ),
    );
    return box;
  }

  const wrong = _errors(looked.body);
  if (wrong.length) {
    // The system's own words. Ours would be a translation of a message written
    // by the people who know what it means.
    for (const one of wrong) box.append(_line("detail", one));
    return box;
  }

  const read = looked.read;
  if (!read) {
    box.append(_line("detail", _short(looked)));
    return box;
  }

  // The answer, said. `sentence` is the reader's own and is deterministic --
  // counted and named from the payload, never summarised by a model, because
  // "16" has to be 16.
  if (read.sentence) box.append(_line("said", read.sentence));

  const records = read.records || [];
  if (!records.length) return box;

  if (!open) {
    const show = document.createElement("button");
    show.type = "button";
    show.className = "quiet";
    show.textContent = "show";
    show.addEventListener("click", () => onOpen?.());
    box.append(show);
    return box;
  }

  // The record somebody asked about, first.
  //
  // "is there a customer type called KKYT" was answered with eight rows of
  // whatever the system returned first, and KKYT was not among them -- an
  // answer that contains the answer and does not show it.
  const ordered = _ordered(records, asked);
  box.append(_cards(ordered, read.columns || [], asked, read));
  return box;
}

/** The records as cards, a page at a time.
 *
 * A table in this column could not be read. Ten fields of a warehouse record
 * across 360 pixels is a horizontal scroller, and what falls off the right is
 * arbitrary -- measured on the deployment 2026-09-21, the visible columns were
 * `LONGDESCRIPTION | RESOURCEID | INVENTORYSTATUSPROGRESSION | VE…` and the
 * reader had to drag sideways to learn anything else. A card reads downwards,
 * which is the direction this panel already has room in.
 *
 * And a page at a time, because "first 8 of 110 -- the rest are in the
 * console" is this panel telling somebody to go and use a different product.
 * 110 records is not a report; it is a list somebody can page through where
 * they are standing.
 *
 * The page lives in this closure. The ledger redraws only when its signature
 * changes, so paging survives a poll -- and a redraw that DOES happen is one
 * where something was said, which is a reasonable moment to be back at the
 * first page.
 */
function _cards(records, columns, asked, read) {
  const holder = document.createElement("div");
  holder.className = "records";
  const list = document.createElement("ul");
  list.className = "record-list";
  const foot = document.createElement("p");
  foot.className = "note";

  const pages = Math.max(1, Math.ceil(records.length / K_ROWS));
  let page = 0;

  const draw = () => {
    list.replaceChildren();
    const from = page * K_ROWS;
    for (const record of records.slice(from, from + K_ROWS)) {
      list.append(_card(record, columns, asked));
    }
    const last = Math.min(from + K_ROWS, records.length);
    const counted = read.counted;
    // What is on this page, of what there is. `+` where more exist than
    // crossed the wire, so the number is never read as the whole set.
    const whole =
      counted === null || counted === undefined
        ? `${records.length}+`
        : String(counted);
    foot.textContent = `${from + 1}–${last} of ${whole}`;
  };

  if (pages > 1) {
    const back = document.createElement("button");
    back.type = "button";
    back.className = "quiet";
    back.textContent = "←";
    back.setAttribute("aria-label", "previous records");
    const on = document.createElement("button");
    on.type = "button";
    on.className = "quiet";
    on.textContent = "→";
    on.setAttribute("aria-label", "more records");
    const settle = () => {
      back.disabled = page === 0;
      on.disabled = page >= pages - 1;
    };
    back.addEventListener("click", () => {
      page = Math.max(0, page - 1);
      draw();
      settle();
    });
    on.addEventListener("click", () => {
      page = Math.min(pages - 1, page + 1);
      draw();
      settle();
    });
    draw();
    settle();
    const paging = document.createElement("div");
    paging.className = "paging";
    paging.append(back, foot, on);
    holder.append(list, paging);
    return holder;
  }

  draw();
  holder.append(list, foot);
  return holder;
}

/** One record, read downwards.
 *
 * The first column is the heading: `answer.py` ranks the columns and puts the
 * identifying one first -- a code, a name, a description -- so the heading is
 * what a person would call this record rather than whichever field the system
 * happened to serialise first.
 */
function _card(record, columns, asked) {
  const item = document.createElement("li");
  item.className = "record";
  const words = _distinguishing(_asked(asked), [record]);
  if (words.length && _names(record, words)) item.dataset.asked = "1";

  const [first, ...rest] = columns;
  const head = document.createElement("p");
  head.className = "record-name";
  head.textContent = _value(record[first]);
  item.append(head);

  for (const column of rest) {
    const value = record[column];
    // A field this record does not carry is left out entirely rather than
    // drawn as a dash. A table needs every row to have every column; a card
    // does not, and eight dashes under a heading is a card that says nothing.
    if (value === undefined || value === null || value === "") continue;
    const line = document.createElement("p");
    line.className = "record-field";
    const name = document.createElement("span");
    name.className = "record-label";
    name.textContent = column;
    const said = document.createElement("span");
    said.className = "record-value";
    said.textContent = _value(value);
    line.append(name, said);
    item.append(line);
  }
  return item;
}

function _value(value) {
  if (value === undefined || value === null || value === "") return "—";
  const said = String(value);
  return said.length > K_CELL ? said.slice(0, K_CELL) + "…" : said;
}

/** The records, with the ones the question names at the front.
 *
 * Stable otherwise: a system's own order is a fact about the system, and
 * shuffling what nobody asked about would be this panel inventing a ranking.
 */
function _ordered(records, asked) {
  const words = _distinguishing(_asked(asked), records);
  if (!words.length) return records;
  const hit = (record) => _names(record, words);
  const named = records.filter(hit);
  return named.length
    ? [...named, ...records.filter((record) => !hit(record))]
    : records;
}

/** The words that actually tell these records apart.
 *
 * Measured on the deployment 2026-09-21. Asked "is there a customer type
 * called KKYT" over 110 records, every word of the question was matched
 * against every value -- and `type` appears in forty descriptions ("leaning
 * new SRO type 004"), `customer` in another. Forty records were promoted
 * ahead of the one the question named, and KKYT was not in the eight drawn.
 *
 * A word that matches most of the result distinguishes nothing; a word that
 * matches a few is the one somebody typed to find them. So the bar is how
 * much of the result a word picks out, not how long it is or whether somebody
 * listed it as common. `kkyt` picks out one of 110 and stays; `type` picks out
 * forty and goes.
 */
function _distinguishing(words, records) {
  if (!records.length) return words;
  const most = Math.max(1, Math.floor(records.length * K_TELLING));
  return words.filter((word) => {
    const picks = records.filter((record) => _names(record, [word])).length;
    return picks > 0 && picks <= most;
  });
}

function _names(record, words) {
  return Object.values(record).some((value) => {
    const said = String(value ?? "").toLowerCase();
    return said && words.some((word) => said.includes(word));
  });
}

/** The words of a question worth matching a VALUE against.
 *
 * Long enough not to match everything, and values only, never column names:
 * `customer` and `type` are in every key on this endpoint and in none of the
 * records, so matching keys would put every record first -- which is the same
 * as none.
 */
function _asked(asked) {
  return String(asked || "")
    .split(/[^A-Za-z0-9]+/)
    .map((word) => word.toLowerCase())
    .filter((word) => word.length > 2 && !_COMMON.has(word));
}

const _COMMON = new Set([
  "the",
  "and",
  "for",
  "are",
  "was",
  "there",
  "that",
  "this",
  "with",
  "what",
  "which",
  "how",
  "many",
  "any",
  "does",
  "has",
  "have",
  "been",
  "called",
  "named",
  "show",
  "list",
  "get",
  "set",
  "all",
  "count",
  "from",
  "into",
]);

/** What the system said went wrong, in its own words.
 *
 * Off the raw body, because an error body is not records and never reaches
 * the reader.
 */
function _errors(body) {
  if (typeof body !== "string" || !body.trim()) return [];
  let said;
  try {
    said = JSON.parse(body);
  } catch {
    return [];
  }
  if (!said || typeof said !== "object" || !Array.isArray(said.errors))
    return [];
  return said.errors
    .filter((one) => one && typeof one === "object")
    .map((one) =>
      [one.errorCode, one.userMessage || one.message]
        .filter(Boolean)
        .join(" — "),
    )
    .filter(Boolean);
}

/** A sight of an answer that is not records: one record, a number, a page. */
function _short(looked) {
  if (typeof looked.body === "string" && looked.body.trim()) {
    const said = looked.body.replace(/\s+/g, " ").trim();
    return said.length > 240 ? said.slice(0, 240) + "…" : said;
  }
  const seen = looked.seen || {};
  if (seen.text_digest)
    return `the screen came up (${String(seen.text_digest).slice(0, 24)})`;
  return looked.status ? `answered ${looked.status}` : "answered";
}

function _line(className, text) {
  const line = document.createElement("p");
  line.className = className;
  line.textContent = text;
  return line;
}
