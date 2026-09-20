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
  box.append(_table(ordered, read.columns || [], asked));

  const counted = read.counted;
  const total =
    counted === null || counted === undefined
      ? `${records.length}+`
      : String(counted);
  if (ordered.length > K_ROWS || (counted ?? 0) > K_ROWS) {
    box.append(
      _line(
        "note",
        `first ${K_ROWS} of ${total} — the rest are in the console`,
      ),
    );
  }
  return box;
}

/** The records, with the ones the question names at the front.
 *
 * Stable otherwise: a system's own order is a fact about the system, and
 * shuffling what nobody asked about would be this panel inventing a ranking.
 */
function _ordered(records, asked) {
  const words = _asked(asked);
  if (!words.length) return records;
  const hit = (record) => _names(record, words);
  const named = records.filter(hit);
  return named.length
    ? [...named, ...records.filter((record) => !hit(record))]
    : records;
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

function _table(records, columns, asked) {
  const scroll = document.createElement("div");
  // Its own scroller. A wide table must not make the whole panel scroll
  // sideways, which takes the composer and every card with it.
  scroll.className = "rows";
  const table = document.createElement("table");

  const head = document.createElement("tr");
  for (const column of columns) {
    const cell = document.createElement("th");
    cell.textContent = column;
    head.append(cell);
  }
  table.append(head);

  const words = _asked(asked);
  for (const record of records.slice(0, K_ROWS)) {
    const line = document.createElement("tr");
    // Said on the row rather than only implied by its position, so the eye can
    // find it among eight that otherwise look alike.
    if (words.length && _names(record, words)) line.dataset.asked = "1";
    for (const column of columns) {
      const cell = document.createElement("td");
      // An em dash for a field this record does not carry, because an empty
      // cell reads as a value that is blank -- and in a warehouse those are
      // different facts.
      const value = record[column];
      cell.textContent =
        value === undefined || value === null || value === ""
          ? "—"
          : _cell(value);
      line.append(cell);
    }
    table.append(line);
  }
  scroll.append(table);
  return scroll;
}

function _cell(value) {
  const said = String(value);
  return said.length > K_CELL ? said.slice(0, K_CELL) + "…" : said;
}

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
