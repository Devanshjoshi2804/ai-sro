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
export function result(looked, { open = true, onOpen } = {}) {
  if (!looked) return null;
  const box = document.createElement("div");
  box.className = "result";
  box.dataset.ok = String(Boolean(looked.ok));

  const where = document.createElement("p");
  where.className = "where";
  where.textContent = `${looked.system || ""} · ${looked.target || ""}`.trim();
  box.append(where);

  if (!looked.ok) {
    box.append(_line("detail", looked.detail || `answered ${looked.status ?? ""}`.trim()));
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
  count.textContent = `${rows.length} found`;
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

  box.append(_table(rows));
  if (rows.length > K_ROWS) {
    box.append(_line("note", `first ${K_ROWS} of ${rows.length} — the rest are in the console`));
  }
  return box;
}

function _table(rows) {
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

  for (const row of rows.slice(0, K_ROWS)) {
    const line = document.createElement("tr");
    for (const column of columns) {
      const cell = document.createElement("td");
      // An em dash for a field this record does not carry, because an empty
      // cell reads as a value that is blank -- and in a warehouse those are
      // different facts.
      const value = row[column];
      cell.textContent =
        value === undefined || value === null || value === "" ? "—" : _cell(value);
      line.append(cell);
    }
    table.append(line);
  }
  scroll.append(table);
  return scroll;
}

/** The columns worth showing: the ones the first rows agree on, in the order
 * the system put them in. Its order is not arbitrary -- the id and the name
 * come first in every capture in this base. */
function _columns(rows) {
  const seen = [];
  for (const row of rows.slice(0, K_ROWS)) {
    for (const key of Object.keys(row)) {
      if (!seen.includes(key)) seen.push(key);
    }
  }
  return seen.slice(0, K_COLUMNS);
}

function _cell(value) {
  const said = typeof value === "object" ? JSON.stringify(value) : String(value);
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
  if (Array.isArray(said)) return said.every((one) => one && typeof one === "object") ? said : null;
  if (said && typeof said === "object" && Array.isArray(said.data)) {
    return said.data.every((one) => one && typeof one === "object") ? said.data : null;
  }
  return null;
}

/** What the system said went wrong, in its own words. */
function _errors(said) {
  if (!said || typeof said !== "object" || !Array.isArray(said.errors)) return [];
  return said.errors
    .filter((one) => one && typeof one === "object")
    .map((one) =>
      [one.errorCode, one.userMessage || one.message].filter(Boolean).join(" — "),
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
  if (seen.text_digest) return `the screen came up (${String(seen.text_digest).slice(0, 24)})`;
  return looked.status ? `answered ${looked.status}` : "answered";
}

function _line(className, text) {
  const line = document.createElement("p");
  line.className = className;
  line.textContent = text;
  return line;
}
