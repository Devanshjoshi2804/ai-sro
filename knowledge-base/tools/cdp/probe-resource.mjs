/*
 * probe-resource.mjs — record exchanges for a resource in an ISOLATED tab.
 *
 * Why its own tab: another capture may be navigating the main page, and two drivers sharing one
 * tab is exactly the stale-frame corruption that has cost this project a day — correct URL,
 * correct title, wrong DOM. This opens its own page in the SAME browser context (so it inherits
 * the session and needs no login), does API-only work, and closes only what it opened.
 *
 * Default mode is READ-ONLY. `locations` in particular backs 25k+ real rows, and `codes` is a
 * shared code-list that 16 screens read for their dropdowns; neither has a single stored exchange
 * today, which is precisely why their documented write behaviour is unverifiable.
 *
 *   node tools/cdp/probe-resource.mjs read locations
 *   node tools/cdp/probe-resource.mjs read codes
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const HTTP_DIR = 'knowlegde_graph/blue-yonder-sce/http';
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

const exchange = (page, method, urlPath, body) => page.evaluate(
  async ({ method, urlPath, body, base }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;
    let res, text = '';
    try {
      res = await w.fetch(base + urlPath, { method, credentials: 'include', headers, body: body ? JSON.stringify(body) : undefined });
      text = await res.text();
    } catch (e) { return { networkError: String(e).slice(0, 160), requestHeaders: headers }; }
    const rh = {}; res.headers.forEach((v, k) => { rh[k] = v; });
    // The two 404 shapes must stay distinguishable: only an errors[] 404 proves a record is gone.
    let kind = 'OK';
    if (res.status === 404) {
      kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    } else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
    let parsed = null; try { parsed = JSON.parse(text); } catch {}
    return { requestHeaders: headers, status: res.status, statusText: res.statusText, responseHeaders: rh, body: parsed, bodyRaw: parsed ? null : text.slice(0, 3000), kind };
  }, { method, urlPath, body, base: BASE });

function record(resource, rec) {
  const dir = path.join(HTTP_DIR, 'exchanges');
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(path.join(dir, `${resource}.jsonl`), JSON.stringify(rec) + '\n');
}

async function probe(page, resource, caseName, method, urlPath, body, notes) {
  const r = await exchange(page, method, urlPath, body);
  const rec = {
    ts: new Date().toISOString(), tool: 'tools/cdp/probe-resource.mjs', case: caseName,
    request: { method, url: urlPath.split('?')[0], query: Object.fromEntries(new URLSearchParams(urlPath.split('?')[1] || '')), headers: strip(r.requestHeaders), body: body ?? null },
    response: r.networkError ? { networkError: r.networkError }
      : { status: r.status, statusText: r.statusText, headers: strip(r.responseHeaders), body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
    notes: notes || null,
  };
  record(resource, rec);
  const n = Array.isArray(r.body?.data) ? r.body.data.length : (r.body?.data ? 1 : 0);
  console.log(`  ${caseName.padEnd(24)} ${method} ${urlPath.split('?')[0].padEnd(34)} -> ${r.status ?? 'ERR'} ${r.kind ?? ''} ${n ? `(${n} rows)` : ''}`);
  return rec;
}

/* Read-only reconnaissance: establishes the response SHAPE and the error contract for a resource
 * without creating anything. This is the dimension missing on 312 of 316 screens. */
const READ_PLANS = {
  locations: [
    ['route-exists', 'GET', '/wm/locations?query=[]&offset=0&limit=1&siteId=SG&subsites=----'],
    ['read-collection', 'GET', '/wm/locations?query=[]&offset=0&limit=3&siteId=SG&subsites=----'],
    ['read-missing', 'GET', '/wm/locations/ZZDOESNOTEXIST0001'],
    ['read-batch-route', 'GET', '/wm/locations/batch',
      'Does the documented batch CREATE path exist as a route at all? ROUTE-MISSING here would falsify the recipe the same way transportEquipmentTypes was falsified.'],
    ['count', 'GET', '/wm/locations/count?siteId=SG&subsites=----'],
  ],
  codes: [
    ['route-exists', 'GET', '/wm/codes?columnName=locacc&siteId=SG&subsites=----'],
    ['read-collection', 'GET', '/wm/codes?columnName=dck_acc_cod&siteId=SG&subsites=----'],
    ['read-missing', 'GET', '/wm/codes/ZZDOESNOTEXIST0001'],
    ['read-by-compound-id', 'GET', '/wm/codes/AIR*!trlr_typ',
      'The compound id shape {code}*!{columnName}, and the real backing resource for the falsified transportEquipmentTypes path.'],
    ['read-no-columnname', 'GET', '/wm/codes?siteId=SG&subsites=----',
      'Is columnName mandatory? Recipes treat /wm/codes as one resource partitioned by it.'],
  ],
};

/*
 * Write lifecycles. Each creates ONE throwaway record and ends by proving it is gone with a
 * RECORD-MISSING 404 — not a bare 404, which a nonexistent route also returns forever.
 *
 * codes is safe to exercise: it is a code-list table, and the chosen partition (locacc,
 * Location Access Groups) was already used for throwaway records in earlier sessions. It is also
 * the most shared resource in the app - 4350 rows across 583 columnName partitions - so its write
 * contract being unrecorded was the largest single evidence gap.
 */
async function writeCycle(page, resource, coll, makeBody, idOf, mutField) {
  const stamp = 'ZV' + String(Date.now() % 10000);
  const body = makeBody(stamp);
  const created = await probe(page, resource, 'create-valid', 'POST', coll, body,
    'Throwaway record; the cycle ends by deleting it and proving it gone.');
  const id = idOf(created.response?.body?.data) || null;
  if (!id) { console.log('  ! no resourceId returned - cannot verify or clean up'); return; }
  const idPath = `${coll}/${encodeURIComponent(id)}`;

  await probe(page, resource, 'create-duplicate', 'POST', coll, body, 'Uniqueness contract at the API layer.');
  await probe(page, resource, 'create-empty', 'POST', coll, {}, 'Which fields the SERVER enforces.');
  const read = await probe(page, resource, 'read-created', 'GET', idPath, undefined, 'A create is never proven by its own response.');

  const rec = read.response?.body?.data;
  if (rec && mutField) {
    const put = { ...rec, [mutField]: 'ZV updated' };
    delete put.self_uri;
    await probe(page, resource, 'update-valid', 'PUT', idPath, put);
    const after = await probe(page, resource, 'read-updated', 'GET', idPath, undefined,
      'A 200 on PUT does not mean the field persisted.');
    console.log(`  persisted=${after.response?.body?.data?.[mutField] === 'ZV updated'}`);
  }
  await probe(page, resource, 'delete-valid', 'DELETE', idPath);
  await probe(page, resource, 'delete-again', 'DELETE', idPath, undefined, 'Idempotency is per-resource here.');
  const gone = await probe(page, resource, 'confirm-gone', 'GET', idPath, undefined,
    'MUST be RECORD-MISSING; ROUTE-MISSING would mean the cycle proved nothing.');
  console.log(`  VERDICT: ${gone.response?.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + gone.response?.kind + ')'}`);
}

const WRITE_PLANS = {
  codes: (page) => writeCycle(page, 'codes', '/wm/codes',
    (s) => ({ codeValue: s, columnName: 'locacc', longDescription: 'ZV probe', shortDescription: 'ZV', sortSequence: 99, requiredFlag: 0 }),
    (d) => d?.resourceId, 'longDescription'),
};

const [mode, resource] = process.argv.slice(2);
if (mode !== 'read' && mode !== 'write') { console.error('usage: read|write <resource>'); process.exit(1); }
const plan = mode === 'read' ? READ_PLANS[resource] : WRITE_PLANS[resource];
if (!plan) { console.error(`no ${mode} plan for`, resource); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();            // isolated: never touches another run's tab
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);
  console.log(`\n${resource} — ${mode} probes\n`);
  if (mode === 'read') {
    for (const [name, method, url, notes] of plan) await probe(page, resource, name, method, url, undefined, notes);
  } else {
    await plan(page);
  }
} finally {
  await page.close().catch(() => {});        // close only our own page
}
process.exit(0);                             // do NOT browser.close(): it would close other runs' pages
