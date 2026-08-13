/*
 * api.mjs — issue authenticated API calls through the CDP-attached browser.
 *
 * Runs fetch inside the app's own page, so the session cookie and CSRF header come from the
 * live app and no credential is ever read, passed on a command line, or written to disk.
 *
 *   node tools/cdp/api.mjs GET    /wm/customerTypes/ZVC1
 *   node tools/cdp/api.mjs DELETE /wm/customerTypes/ZVC1
 *   node tools/cdp/api.mjs sweep
 */
import { chromium } from 'playwright';

/*
 * Every record this tooling creates is prefixed ZV. Match the PREFIX, never an enumerated list:
 * an earlier hard-coded list drifted from what the harness actually created (ZVS1, ZVCU1, ZVP1,
 * ZVV1, ZVCL1) and the sweep reported a clean environment while records were still live. A
 * cleanup check that can silently go stale is worse than none.
 */
const MARKERS = /\bZV[A-Z]{0,3}\d*\b|ZZVER|ZZAUDIT|ZV [Cc]ap/;

export async function withPage(fn) {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers/portal'))
    || browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
    || browser.contexts()[0].pages()[0];
  try { return await fn(page); } finally { await browser.close(); }
}

/*
 * Classifies the two structurally different 404s this deployment returns. Conflating them is
 * what allowed a dead endpoint (/wm/transportEquipmentTypes) to sit in write-endpoints.json
 * marked verified: its delete proof was "a later GET returned 404", which a nonexistent route
 * satisfies forever. Only RECORD-MISSING proves a delete.
 */
export const call = (page, method, path, body) =>
  page.evaluate(async ({ method, path, body }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;
    const res = await w.fetch('https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM' + path, {
      method, credentials: 'include', headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let kind = 'OK';
    if (res.status === 404) {
      kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING'
        : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    } else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
    let json = null; try { json = JSON.parse(text); } catch {}
    return { status: res.status, kind, data: json && 'data' in json ? json.data : json, text: text.slice(0, 300) };
  }, { method, path, body });

/* Full proof-of-life cycle for one created record: readable, then deleted, then provably gone. */
export async function lifecycle(page, collection, id, putField) {
  const p = `${collection}/${encodeURIComponent(id)}`;
  const out = { id, steps: [] };
  const g1 = await call(page, 'GET', p);
  out.steps.push(`GET ${g1.status}/${g1.kind}`);
  if (g1.kind !== 'OK') { out.verdict = 'NOT-READABLE'; return out; }
  if (putField) {
    const rec = { ...g1.data, [putField]: 'ZV updated' };
    delete rec.self_uri;
    const pu = await call(page, 'PUT', p, rec);
    const g2 = await call(page, 'GET', p);
    out.steps.push(`PUT ${pu.status} persisted:${g2.data?.[putField] === 'ZV updated'}`);
  }
  const d = await call(page, 'DELETE', p);
  out.steps.push(`DELETE ${d.status}`);
  const g3 = await call(page, 'GET', p);
  out.steps.push(`GET ${g3.status}/${g3.kind}`);
  out.verdict = g3.kind === 'RECORD-MISSING' ? 'PASS'
    : g3.kind === 'ROUTE-MISSING' ? 'CIRCULAR-PROOF-ROUTE-DEAD'
    : g3.kind === 'OK' ? 'DELETE-DID-NOT-DELETE' : 'INCONCLUSIVE';
  return out;
}

/* Safety net: nothing this tooling creates may be left in a shared environment. */
export async function sweep(page) {
  const cols = ['clientGroups', 'customerTypes', 'transportModes', 'equipmentTypes', 'locationTypes',
    'levelTypes', 'businessUnits', 'carriers', 'printers', 'suppliers', 'clients', 'customers',
    'addresses', 'carrierProNumbers', 'carrierCrossReferences', 'areas', 'buildings',
    // devices was missing from this list while the harness was actively creating devices
    // (workstations and voice devices both persist here) - the sweep reported clean regardless.
    'devices', 'clientWarehouse', 'packingConfigurations'];
  const found = [];
  for (const c of cols) {
    const q = c === 'transportModes' ? '?query=[]&offset=0&limit=500'
      : '?query=[]&offset=0&limit=500&siteId=SG&subsites=----';
    const r = await call(page, 'GET', `/wm/${c}${q}`);
    if (r.kind !== 'OK' || !Array.isArray(r.data)) continue;
    for (const row of r.data) if (MARKERS.test(JSON.stringify(row))) found.push({ c, id: row.resourceId });
  }
  return found;
}

// Only act as a CLI when run directly — importing this module must not execute argv.
const isEntry = process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop());
const [cmd, path] = isEntry ? process.argv.slice(2) : [];
if (cmd === 'sweep') {
  console.log(JSON.stringify(await withPage(sweep), null, 1));
} else if (cmd) {
  console.log(JSON.stringify(await withPage((p) => call(p, cmd.toUpperCase(), path)), null, 1));
}
