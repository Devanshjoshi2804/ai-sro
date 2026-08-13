/* customerTypes was verified through the UI on 2026-08-12 but never had catalogue entries,
 * so write_api (allowlist-only by method+pathPattern) could not reach the newest proven screen. */
import fs from 'node:fs';
const P = 'knowlegde_graph/blue-yonder-sce/index/write-endpoints.json';
const e = JSON.parse(fs.readFileSync(P, 'utf8'));
const has = (m, p) => e.some((x) => x.method === m && x.pathPattern === p);
const base = {
  resource: 'customerTypes', verified: true, verified_at: '2026-08-12', reverified_at: '2026-08-12',
  reverify_method: 'tools/cdp/capture.mjs UI capture + tools/cdp/api.mjs lifecycle (GET -> PUT persisted -> DELETE -> GET RECORD-MISSING).',
  id_shape: 'bare code',
  gotcha: 'Description key is longDescription, not description. API ships a typo: shotDescription (sic). csttyp truncates at 4 chars.',
};
const added = [];
if (!has('POST', '/data/WM/wm/customerTypes')) {
  e.push({ method: 'POST', pathPattern: '/data/WM/wm/customerTypes', ...base,
    payload: { customerType: '<=4 chars>', longDescription: '<text>', shotDescription: '', crossDockFlag: -1, bulkPickingFlag: false, outboundDateWindowUnit: 'MIN' },
    notes: 'Configuration > Partners > Customers > Customer Types. 76 real types pre-exist. Added to the catalogue 2026-08-12 — the screen was verified earlier but had no entry, so write_api could not reach it.' });
  added.push('POST');
}
if (!has('DELETE', '/data/WM/wm/customerTypes/{id}')) {
  e.push({ method: 'DELETE', pathPattern: '/data/WM/wm/customerTypes/{id}', ...base,
    notes: '200, confirmed by a following GET returning a RECORD-MISSING 404 (app error envelope), not a ROUTE-MISSING 404.' });
  added.push('DELETE');
}
if (!has('PUT', '/data/WM/wm/customerTypes/{id}')) {
  e.push({ method: 'PUT', pathPattern: '/data/WM/wm/customerTypes/{id}', ...base,
    notes: 'Verified by mutating longDescription on a harness-created record and confirming via a separate GET.' });
  added.push('PUT');
}
fs.writeFileSync(P, JSON.stringify(e, null, 2) + '\n');
console.log('added customerTypes entries:', added.join(', ') || 'none');
console.log('total entries:', e.length);
