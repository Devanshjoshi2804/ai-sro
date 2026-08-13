/*
 * build-matrix.mjs — derive http/status-matrix.json from the recorded exchanges.
 *
 * The matrix is a DERIVED view: every cell points back at exchanges actually stored in
 * http/exchanges/*.jsonl. Nothing is asserted here that was not observed, which is the whole
 * point of the store — the previous ledger's failure was claims with no retrievable evidence.
 */
import fs from 'node:fs';
import path from 'node:path';

const EX = 'knowlegde_graph/blue-yonder-sce/http/exchanges';
const OUT = 'knowlegde_graph/blue-yonder-sce/http/status-matrix.json';

const files = fs.existsSync(EX) ? fs.readdirSync(EX).filter((f) => f.endsWith('.jsonl')) : [];
const matrix = {};
const byCase = {};

for (const f of files) {
  const resource = f.replace('.jsonl', '');
  const recs = fs.readFileSync(path.join(EX, f), 'utf8').split('\n').filter(Boolean).map(JSON.parse);
  const cases = {};
  for (const r of recs) {
    const status = r.response?.status ?? 'NETWORK-ERROR';
    const kind = r.response?.kind ?? null;
    // Last observation wins per case, but keep the count so flapping is visible.
    cases[r.case] = cases[r.case] || { observations: 0 };
    cases[r.case].observations++;
    cases[r.case].status = status;
    cases[r.case].kind = kind;
    cases[r.case].method = r.request.method;
    cases[r.case].url = r.request.url;
    const err = r.response?.body?.errors?.[0];
    if (err) cases[r.case].userMessage = err.userMessage;
    if (r.response?.body?.message) cases[r.case].message = r.response.body.message;
    byCase[r.case] = byCase[r.case] || {};
    byCase[r.case][resource] = `${status}${kind && kind !== 'OK' ? '/' + kind : ''}`;
  }
  matrix[resource] = { evidence: `http/exchanges/${f}`, exchanges: recs.length, cases };
}

const out = {
  generated_from: 'http/exchanges/*.jsonl',
  generated_by: 'tools/cdp/build-matrix.mjs',
  note: 'Derived view. Every cell is backed by a stored request/response pair; nothing here is asserted.',
  resources: matrix,
  by_case: byCase,
};
fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');

// Console view: the cross-resource comparison is where inconsistent behaviour shows up.
const resources = Object.keys(matrix);
const cases = Object.keys(byCase);
console.log('resources:', resources.length, '| total exchanges:',
  Object.values(matrix).reduce((a, b) => a + b.exchanges, 0));
console.log('\ncase'.padEnd(20) + resources.map((r) => r.slice(0, 11).padStart(13)).join(''));
for (const c of cases) {
  console.log(c.padEnd(20) + resources.map((r) => String(byCase[c][r] ?? '-').padStart(13)).join(''));
}
