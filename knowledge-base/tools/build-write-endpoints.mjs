/*
 * build-write-endpoints.mjs — derive the write catalogue from the evidence store.
 *
 * `write-endpoints.json` was hand-maintained: 57 entries, each asserting a verified endpoint and a
 * payload. Coverage reads it, so a proven write only counted once someone remembered to add a row —
 * seven fresh round-trips landed in `http/exchanges` last run and moved the number not at all.
 *
 * This regenerates it from the exchanges instead. An endpoint is `verified` here only if a stored
 * 2xx exists, and it carries `proof: round-trip` only if that resource's cycle ended in a
 * `confirm-gone` that returned RECORD-MISSING — the one shape that actually proves a delete.
 *
 * Hand-written entries are kept when the evidence does not cover them, and marked as such, so the
 * old work is not silently discarded — but where the two disagree, the exchange wins.
 *
 *   node tools/build-write-endpoints.mjs
 */
import fs from 'node:fs';
import path from 'node:path';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/write-endpoints.json`;

/*
 * The hand-written baseline is read from its OWN file, never from this script's output. Reading the
 * output made the generator non-idempotent: a second run counted its own derived rows as
 * hand-written and the catalogue grew from 88 entries to 180.
 */
const prior = JSON.parse(fs.readFileSync(`${KG}/index/write-endpoints.handwritten.json`, 'utf8'));
const priorList = Array.isArray(prior) ? prior : Object.values(prior);

const CASE_METHOD = {
  'create-valid': 'POST', 'create-valid-full-model': 'POST',
  'create-valid-sampled-row': 'POST', 'create-valid-via-codes': 'POST',
  'create-valid-composite': 'POST', 'create-valid-ui-captured': 'POST',
  'update-valid': 'PUT', 'delete-valid': 'DELETE', 'delete-via-codes': 'DELETE',
};
const derived = new Map();     // resource|method -> entry

for (const file of fs.readdirSync(EX)) {
  const resource = file.replace('.jsonl', '');
  let roundTrip = false;
  const rows = fs.readFileSync(path.join(EX, file), 'utf8').trim().split('\n').filter(Boolean).map((l) => {
    try { return JSON.parse(l); } catch { return null; }
  }).filter(Boolean);

  for (const r of rows) {
    if ((r.case === 'confirm-gone' || r.case === 'cleanup-confirm-gone') && r.response?.kind === 'RECORD-MISSING') roundTrip = true;
  }

  for (const r of rows) {
    const method = CASE_METHOD[r.case];
    if (!method) continue;
    const status = r.response?.status;
    if (!(status >= 200 && status < 300)) continue;

    /*
     * The path comes from the request that actually worked, not from the resource's name. They
     * differ for view resources: `uoms` is a read view over `/wm/codes`, and its create really is
     * `POST /wm/codes`. Naming the view here would document an endpoint that returns 422.
     */
    const url = String(r.request?.url || '').replace(/^\/wm\//, '/data/WM/wm/');
    const key = `${resource}|${method}|${url}`;
    const existing = derived.get(key);
    const entry = existing || {
      method,
      // For PUT/DELETE the recorded url already carries a concrete id; replace it rather than append.
      pathPattern: method === 'POST' ? url : url.replace(/\/[^/]+$/, '/{id}'),
      resource,
      // Only meaningful on the create: a DELETE path already names the route it acts on.
      creates_through: method === 'POST' && !url.includes(`/wm/${resource}`) ? url : undefined,
      verified: true,
      source: 'derived from http/exchanges',
      proof: roundTrip ? 'round-trip' : 'observed',
      evidence: `http/exchanges/${resource}.jsonl`,
      cases: [],
    };
    if (!entry.cases.includes(r.case)) entry.cases.push(r.case);
    // The payload is the body that actually worked, not a reconstruction.
    if (method === 'POST' && r.request?.body && !entry.payload) entry.payload = r.request.body;
    if (roundTrip) entry.proof = 'round-trip';
    entry.verified_at = (r.ts || '').slice(0, 10);
    derived.set(key, entry);
  }
}

/* Keep hand-written rows the evidence does not cover, flagged so the difference stays visible. */
const kept = priorList.filter((e) => !derived.has(`${e.resource}|${e.method}`))
  .map((e) => ({ ...e, source: e.source || 'hand-written, not corroborated by a stored exchange', proof: e.proof || 'asserted' }));

const list = [...derived.values(), ...kept].sort((a, b) => (a.resource + a.method).localeCompare(b.resource + b.method));
fs.writeFileSync(OUT, JSON.stringify(list, null, 2) + '\n');

const byProof = list.reduce((a, e) => (a[e.proof] = (a[e.proof] || 0) + 1, a), {});
console.log(JSON.stringify({
  entries: list.length,
  derived_from_exchanges: derived.size,
  kept_hand_written: kept.length,
  by_proof: byProof,
  resources_with_a_proven_create: new Set(list.filter((e) => e.method === 'POST' && e.payload).map((e) => e.resource)).size,
}, null, 1));
