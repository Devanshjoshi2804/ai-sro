// What one lookup came back with, as something a person can read.
//
// The panel has been showing 240 characters of raw JSON per system. That is a
// preview of an answer rather than an answer: "how many suppliers are at SG"
// gets `{"data":[{"supplierNumber":"100012","supplierName":"ACME LOGIS` and the
// person counts nothing.
//
// Five states, because a lookup has five ends and four of them are not rows:
//
//   1. The system refused        -- status and what it said.
//   2. The system answered with an ERROR body -- its own words, which are
//      better than ours: `errorCode` and `userMessage`.
//   3. Rows                      -- the count first, then a table of the first
//      few.
//   4. Answered, and not a list  -- one record, a number, a string: shown as
//      it came, trimmed.
//   5. Nothing to show           -- a screen lookup, whose picture is
//      deliberately not on this side of the wire.
//
// **Where the rows are is measured, not guessed.** Across the 296 captured
// exchange files in this repository's knowledge base, 88 of the list responses
// put their rows under `data` and three carry `errors`; nothing else is a row
// list. So `data` is the rule, a top-level array is accepted because it costs
// nothing, and anything else is state 4 rather than a search for arrays.
//
// **The count is the product.** A person asking "how many" has been answered
// the moment they read it, and the table is what they check it against -- so
// the count is the first thing, in its own line, and the table is eight rows
// of it. Not a pager: a panel beside a warehouse screen is not where somebody
// reads two hundred rows, and what reads them is the console.
//
// Pure, and given the answer rather than fetching it.

/** How many rows this panel shows. Eight is what fits beside a warehouse
 * screen without the card becoming the screen. */
export const K_ROWS = 8;

/** How many columns. A warehouse record has forty fields and six of them are
 * what somebody asked about; the rest make a table nobody can read on a
 * 360-pixel column. */
export const K_COLUMNS = 6;

/** How much of one cell. Long enough for a description, short enough that one
 * fat field cannot push every other column off the panel. */
export const K_CELL = 40;

/**
 * The card, or `null` when there is nothing to say at all.
 *
 * `open` is whether this is the turn somebody is looking at. An older answer
 * collapses to its count, because a conversation with four tables in it is a
 * conversation nobody scrolls.
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

  const said = _body(looked.body);
  const wrong = _errors(said);
  if (wrong.length) {
    // The system's own words. Ours would be a translation of a message written
    // by the people who know what it means.
    for (const one of wrong) box.append(_line("detail", one));
    return box;
  }

  const rows = _rows(said);
  if (rows === null) {
    box.append(_line("detail", _short(looked)));
    return box;
  }

  const count = document.createElement("p");
  count.className = "count";
  // `at least`, where the answer was trimmed on the way here.
  //
  // The body is cut BY RECORD so it stays parseable, which means the count is
  // the count of what arrived and not of what the system holds. Measured on
  // the deployment 2026-09-21: fifty customer types came back, forty
  // survived the trim, and the panel said "40 found" -- a number nobody can
  // act on presented as one they can.
  count.textContent = looked.truncated
    ? `at least ${rows.length} found`
    : `${rows.length} found`;
  box.append(count);
  if (!rows.length) return box;

  if (!open) {
    const show = document.createElement("button");
    show.type = "button";
    show.className = "quiet";
    show.textContent = "show";
    show.addEventListener("click", () => onOpen?.());
    box.append(show);
    return box;
  }

  // The row somebody asked about, first.
  //
  // "is there a customer type called KKYT" was answered with eight rows of
  // the records the system happened to return first, and KKYT was not among
  // them -- an answer that contains the answer and does not show it. The
  // question names the record; the table can put it at the top.
  const ordered = _ordered(rows, asked);
  box.append(_table(ordered, asked));
  if (ordered.length > K_ROWS) {
    const more = looked.truncated
      ? `${ordered.length}+`
      : String(ordered.length);
    box.append(
      _line("note", `first ${K_ROWS} of ${more} — the rest are in the console`),
    );
  }
  return box;
}

/** The rows, with the ones the question names at the front.
 *
 * Stable otherwise: a system's own order is a fact about the system, and
 * shuffling what nobody asked about would be this panel inventing a ranking.
 */
function _ordered(rows, asked) {
  const words = _asked(asked);
  if (!words.length) return rows;
  const hit = (row) =>
    Object.values(row).some((value) => {
      if (value === null || value === undefined || typeof value === "object")
        return false;
      const said = String(value).toLowerCase();
      return words.some((word) => said === word || said.includes(word));
    });
  const named = rows.filter(hit);
  return named.length ? [...named, ...rows.filter((row) => !hit(row))] : rows;
}

/** The words of a question worth matching a VALUE against.
 *
 * Long enough not to match everything, and values only -- `customer` and
 * `type` are in every key on this endpoint and in none of the records, so
 * matching keys would put every row first, which is the same as none.
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

function _table(rows, asked) {
  const columns = _columns(rows);
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
  for (const row of rows.slice(0, K_ROWS)) {
    const line = document.createElement("tr");
    // Said on the row rather than only implied by its position, so the eye
    // can find it in eight rows that otherwise look alike.
    if (
      words.length &&
      Object.values(row).some(
        (value) =>
          value !== null &&
          value !== undefined &&
          typeof value !== "object" &&
          words.some((word) => String(value).toLowerCase().includes(word)),
      )
    ) {
      line.dataset.asked = "1";
    }
    for (const column of columns) {
      const cell = document.createElement("td");
      // An em dash for a field this record does not carry, because an empty
      // cell reads as a value that is blank -- and in a warehouse those are
      // different facts.
      const value = row[column];
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

/** The columns worth showing: the ones that CARRY something, in the order the
 * system put them in.
 *
 * This used to take the first six keys, on the reasoning that a system puts
 * the id and the name first. Blue Yonder alphabetises instead, so the answer
 * to "is there a customer type called KKYT" was
 *
 *     URNFORMAT  ABSOLUTEGROUP  ALLOCATIONSEARCHPATH  ALLOWSOURCE…  BULKPI…
 *         —            —                 —                 —          false
 *
 * five columns of nothing, beside a warehouse screen showing `Customer Type`
 * and `Description`. A column that is empty in every row it is drawn for
 * cannot tell anybody anything, and it costs the one that could.
 *
 * Order is still the system's among the columns that survive: it is a fact
 * about the system, and re-ranking them would be this panel guessing which
 * field matters.
 */
function _columns(rows) {
  const shown = rows.slice(0, K_ROWS);
  const seen = [];
  for (const row of shown) {
    for (const key of Object.keys(row)) {
      if (!seen.includes(key)) seen.push(key);
    }
  }
  const carries = (key) =>
    shown.some((row) => {
      const value = row[key];
      return value !== undefined && value !== null && value !== "";
    });
  const worth = seen.filter(carries);
  // Every column empty is still a table of somethings -- a page of records
  // that are genuinely all blank -- and drawing nothing would be worse than
  // drawing what is there.
  return (worth.length ? worth : seen).slice(0, K_COLUMNS);
}

function _cell(value) {
  const said =
    typeof value === "object" ? JSON.stringify(value) : String(value);
  return said.length > K_CELL ? said.slice(0, K_CELL) + "…" : said;
}

function _body(body) {
  if (typeof body !== "string" || !body.trim()) return null;
  try {
    return JSON.parse(body);
  } catch {
    return body;
  }
}

/** The rows, or `null` where this answer is not a list of records.
 *
 * `data` because that is what the systems in this base answer with: 88 of the
 * captured list responses, against nothing else. A top-level array is taken
 * too -- it costs nothing and is what a plainer API would send.
 */
function _rows(said) {
  if (Array.isArray(said))
    return said.every((one) => one && typeof one === "object") ? said : null;
  if (said && typeof said === "object" && Array.isArray(said.data)) {
    return said.data.every((one) => one && typeof one === "object")
      ? said.data
      : null;
  }
  return null;
}

/** What the system said went wrong, in its own words. */
function _errors(said) {
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

/** A sight of an answer that is not a list: one record, a number, a page. */
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
