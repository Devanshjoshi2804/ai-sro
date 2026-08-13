/*
 * apply-captures.mjs — fold captured request bodies into write-endpoints.json.
 *
 * Turns the ledger from a prose claim list into something executable: each POST entry gains the
 * real body the app sent, captured by driving the actual Add form. Values are replaced with
 * placeholders so the entry reads as a template rather than as one run's test data, while the
 * KEYS — the part that was impossible to derive from the API's own errors — are preserved
 * exactly as the app sends them.
 */
import fs from 'node:fs';

const LEDGER = 'knowlegde_graph/blue-yonder-sce/index/write-endpoints.json';
const CAPTURES = 'knowlegde_graph/blue-yonder-sce/index/captures';
const D = '2026-08-12';

/* Replace only the values this harness injected; leave defaults/flags as the app sent them. */
const templatize = (body) => {
  const o = JSON.parse(body);
  for (const [k, v] of Object.entries(o)) {
    if (typeof v === 'string' && /^ZV/i.test(v)) o[k] = `<${k}>`;
    if (typeof v === 'string' && /^ZV Cap/i.test(v)) o[k] = `<${k}>`;
  }
  return o;
};

const byResource = {};
for (const f of fs.readdirSync(CAPTURES)) {
  const j = JSON.parse(fs.readFileSync(`${CAPTURES}/${f}`, 'utf8'));
  for (const r of (j.requests || [])) {
    if (r.method !== 'POST' || !r.body) continue;
    const resource = r.url.split('/wm/')[1];
    // First capture wins; later screens re-create the same resource with the same shape.
    if (!byResource[resource]) byResource[resource] = { body: templatize(r.body), from: f.replace('.json', '') };
  }
}

const ledger = JSON.parse(fs.readFileSync(LEDGER, 'utf8'));
const applied = [];
for (const entry of ledger) {
  if (entry.method !== 'POST') continue;
  const cap = byResource[entry.resource];
  if (!cap) continue;
  entry.payload = cap.body;
  entry.payload_source = `captured from the live UI Add form on the ${cap.from} screen via tools/cdp/cap.mjs`;
  entry.reverified_at = D;
  applied.push(entry.resource);
}
fs.writeFileSync(LEDGER, JSON.stringify(ledger, null, 2) + '\n');

const posts = ledger.filter((x) => x.method === 'POST');
console.log('payloads applied from captures:', applied.join(', '));
console.log('POST endpoints with an executable payload:', posts.filter((x) => x.payload).length, '/', posts.length);
console.log('still prose-only:', posts.filter((x) => !x.payload).map((x) => x.resource).join(', ') || 'none');
