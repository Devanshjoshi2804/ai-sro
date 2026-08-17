/*
 * trim-exchanges.mjs — cap oversized stored bodies, and record WHY they were oversized.
 *
 * The read-shape sweep asked every collection for `limit=2`. Some resources ignored it:
 * `appointments` returned 7,808 rows, `footprints` 13,069, `userOperations` 13,883 — one exchange
 * of 32 MB for a request that asked for two records. That is worth knowing as a fact about the app
 * (a "read one row to check" can pull an entire table) and not worth keeping as 45 MB of stored
 * customer data.
 *
 * So: keep the first two rows, which is what the shape was derived from, and replace the rest with
 * an explicit marker carrying the real row count and byte size. The evidence is not silently
 * shrunk — the record says what was dropped and why.
 *
 *   node tools/trim-exchanges.mjs --dry
 *   node tools/trim-exchanges.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const SHAPES = `${KG}/index/read-shapes.json`;
const KEEP_ROWS = 2;
const LIMIT_BYTES = 200_000;
const dry = process.argv.includes('--dry');

const shapes = JSON.parse(fs.readFileSync(SHAPES, 'utf8'));
const ignoringLimit = [];
let trimmed = 0, savedBytes = 0;

for (const file of fs.readdirSync(EX)) {
  const p = path.join(EX, file);
  const lines = fs.readFileSync(p, 'utf8').split('\n').filter(Boolean);
  let changed = false;

  const out = lines.map((line) => {
    if (Buffer.byteLength(line) < LIMIT_BYTES) return line;
    let r; try { r = JSON.parse(line); } catch { return line; }
    const data = r.response?.body?.data;
    if (!Array.isArray(data)) return line;

    const asked = Number(r.request?.query?.limit);
    const before = Buffer.byteLength(line);
    if (asked && data.length > asked) {
      const resource = file.replace('.jsonl', '');
      if (!ignoringLimit.includes(resource)) ignoringLimit.push(resource);
    }
    r.response.body.data = data.slice(0, KEEP_ROWS);
    r.response.body_truncated = {
      by: 'tools/trim-exchanges.mjs',
      rows_returned: data.length,
      rows_kept: KEEP_ROWS,
      original_bytes: before,
      why: asked && data.length > asked
        ? `the request asked for limit=${asked} and the server returned ${data.length} rows — this resource ignores limit`
        : 'body exceeded the store\'s size cap',
    };
    changed = true;
    const next = JSON.stringify(r);
    savedBytes += before - Buffer.byteLength(next);
    trimmed++;
    return next;
  });

  if (changed && !dry) fs.writeFileSync(p, out.join('\n') + '\n');
}

/* Mark the offenders in the read-shape index, so a consumer sees it before issuing the request. */
for (const r of ignoringLimit) if (shapes.resources[r]) shapes.resources[r].honours_limit = false;
if (!dry) {
  shapes.caution = 'Some resources IGNORE the limit parameter and return the whole table; they are marked honours_limit:false. A read intended to sample two rows can return tens of thousands.';
  fs.writeFileSync(SHAPES, JSON.stringify(shapes, null, 2) + '\n');
}

console.log(JSON.stringify({
  dry, records_trimmed: trimmed, megabytes_saved: +(savedBytes / 1e6).toFixed(1),
  resources_ignoring_limit: ignoringLimit,
}, null, 1));
