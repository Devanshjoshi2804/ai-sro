/*
 * probe-filterable-columns.mjs — find out WHICH columns a resource will actually filter on.
 *
 * The query grammar works, but not on every column. Filtering `addresses` by `addressId` or
 * `addressName` returns the right row; filtering the same resource by `city`, `state` or
 * `requestState` — with a value copied out of a row that is definitely there — returns 200 and
 * ZERO rows. No error, no warning.
 *
 * That is the most dangerous shape a read can have: an agent asking "is there an address in
 * BURLINGTON" gets a confident "no". So the filterable set has to be measured per resource rather
 * than assumed, and the answer stored where a caller will look before trusting an empty result.
 *
 * Method: take one real row, and for every scalar column try EQ with that row's own value. A
 * column that returns the row is filterable. A column that returns nothing, given a value we know
 * exists, is not.
 *
 * Read-only.
 *
 *   node tools/cdp/probe-filterable-columns.mjs addresses carriers locations items
 *   node tools/cdp/probe-filterable-columns.mjs --status    every resource with a status field
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/filterable-columns.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const MAX_COLUMNS = 24;

const shapes = JSON.parse(fs.readFileSync(`${KG}/index/read-shapes.json`, 'utf8')).resources;
const isStatus = (f) => /(^|[a-z])(status|state)$/i.test(f) && !/desc/i.test(f);

const args = process.argv.slice(2);
const targets = args.includes('--status')
  ? Object.entries(shapes).filter(([, s]) => s.status === 200 && s.honours_limit !== false && (s.fields || []).some((f) => isStatus(f.field))).map(([n]) => n)
  : args.filter((a) => !a.startsWith('--'));
if (!targets.length) { console.error('usage: probe-filterable-columns.mjs <resource>... | --status'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

const get = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  return { status: res.status, body: parsed, sessionExpired: !parsed && /b2clogin|<html|Sign in/i.test(text) };
}, { url, base: BASE });

const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { resources: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(11000);

  for (const resource of targets) {
    const base1 = await get(`/wm/${resource}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`);
    if (base1?.sessionExpired) { console.error('SESSION EXPIRED — nothing recorded.'); process.exit(2); }
    const row = base1.body?.data?.[0];
    if (!row) { console.log(`${resource}: no rows to probe`); continue; }

    /*
     * Probe the identifying columns first. Taking the first 24 keys alphabetically meant `items`
     * spent its whole budget on attributeDate1..attributeText5 and never tested `itemNumber`, then
     * reported that items are filterable on one column — an artifact of the cap, not the app.
     */
    const scalar = Object.keys(row).filter((k) => k !== 'resourceId' && !k.endsWith('_uri')
      && (typeof row[k] === 'string' || typeof row[k] === 'number') && String(row[k]).length > 0);
    const identifying = (k) => /(^|[a-z])(id|code|number|name|status|type|key)$/i.test(k) && !/desc/i.test(k);
    const cols = [...scalar.filter(identifying), ...scalar.filter((k) => !identifying(k))].slice(0, MAX_COLUMNS);

    const filterable = [];
    const notFilterable = [];
    for (const col of cols) {
      const value = row[col];
      const q = encodeURIComponent(JSON.stringify([{ column: col, operator: 'EQ', value }]));
      const r = await get(`/wm/${resource}?query=${q}&offset=0&limit=50&siteId=SG&subsites=----`);
      const rows = Array.isArray(r.body?.data) ? r.body.data : [];
      const ok = rows.length > 0 && rows.every((x) => String(x[col]) === String(value));
      (ok ? filterable : notFilterable).push(col);
    }

    store.resources[resource] = {
      probed_columns: cols.length,
      filterable,
      not_filterable: notFilterable,
      note: notFilterable.length
        ? 'Columns in not_filterable returned 200 with zero rows for a value taken from a real row. An empty result from those proves nothing.'
        : undefined,
    };
    fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/probe-filterable-columns.mjs', case: 'filterable-columns',
      request: { method: 'GET', url: `/wm/${resource}`, query: { query: '[{"column":"<each column>","operator":"EQ","value":"<its own value>"}]' }, headers: { accept: 'application/json' } },
      response: { status: 200, body: { filterable, not_filterable: notFilterable } },
      notes: 'Which columns this resource honours in the query grammar, measured by filtering on a value taken from one of its own rows.',
    }) + '\n');

    console.log(`${resource.padEnd(24)} filterable ${String(filterable.length).padStart(2)}/${cols.length}: ${filterable.slice(0, 6).join(', ')}${filterable.length > 6 ? ' …' : ''}`);
    fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/probe-filterable-columns.mjs', ...store }, null, 2) + '\n');
  }

  const all = Object.values(store.resources);
  console.log(JSON.stringify({
    resources: all.length,
    columns_probed: all.reduce((a, r) => a + r.probed_columns, 0),
    filterable: all.reduce((a, r) => a + r.filterable.length, 0),
    silently_unfilterable: all.reduce((a, r) => a + r.not_filterable.length, 0),
  }, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
