/*
 * capture-read-shapes.mjs — record what every readable resource actually RETURNS.
 *
 * This is the base's largest gap. `coverage.json` reports read_shapes complete on 4 of 316 screens:
 * we know which resources a screen calls, and almost never what comes back. An agent cannot assert a
 * post-condition against a field name it has never seen.
 *
 * Resources are shared across screens, so this closes the dimension broadly rather than screen by
 * screen: one GET per resource, `limit=2`, full response stored.
 *
 * Reads only. No resource is written, and a non-200 is kept — a 400 on a collection that needs a
 * parameter is as much a fact about the contract as a 200.
 *
 *   node tools/cdp/capture-read-shapes.mjs            every collection resource
 *   node tools/cdp/capture-read-shapes.mjs 40         first 40 (smoke run)
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const OUT = `${KG}/index/read-shapes.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

/* Collection endpoints only: `/wm/<resource>` with no id segment and no sub-path. */
const endpoints = JSON.parse(fs.readFileSync(`${KG}/index/api-endpoints.json`, 'utf8'));
const list = Array.isArray(endpoints) ? endpoints : endpoints.endpoints;
const resources = [...new Set(list
  .filter((e) => e.service === 'WM' && /^\/data\/WM\/wm\/[A-Za-z0-9]+$/.test(e.path))
  .map((e) => e.path.replace('/data/WM', '')))].sort();

const limit = Number(process.argv[2]) || resources.length;
const targets = resources.slice(0, limit);

/*
 * Type a value the way a consumer needs it: name, JSON type, whether it was null in this sample, and
 * a short example. Null-in-sample matters — a field that is null on every row we saw is a field no
 * assertion should be written against yet.
 */
function shapeOf(rows) {
  const keys = new Map();
  for (const row of rows) {
    for (const [k, v] of Object.entries(row || {})) {
      const t = v === null ? 'null' : Array.isArray(v) ? 'array' : typeof v;
      const e = keys.get(k) || { field: k, types: new Set(), null_in_sample: false, example: undefined };
      e.types.add(t);
      if (v === null) e.null_in_sample = true;
      else if (e.example === undefined) e.example = typeof v === 'object' ? '<object>' : String(v).slice(0, 40);
      keys.set(k, e);
    }
  }
  return [...keys.values()].map((e) => ({ ...e, types: [...e.types].join('|') }));
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { resources: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  let i = 0, ok = 0;
  for (const res of targets) {
    i++;
    const url = `${res}?query=[]&offset=0&limit=2&siteId=SG&subsites=----`;
    const r = await page.evaluate(async ({ url, base }) => {
      const f = document.querySelector('iframe');
      const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
      let resp, text = '';
      try { resp = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await resp.text(); }
      catch (e) { return { networkError: String(e).slice(0, 160) }; }
      const rh = {}; resp.headers.forEach((v, k) => { rh[k] = v; });
      let parsed = null; try { parsed = JSON.parse(text); } catch {}
      let kind = 'OK';
      if (resp.status === 404) kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
      else if (resp.status < 200 || resp.status >= 300) kind = 'HTTP-' + resp.status;
      return { status: resp.status, statusText: resp.statusText, headers: rh, body: parsed, bodyRaw: parsed ? null : text.slice(0, 1500), kind };
    }, { url, base: BASE }).catch((e) => ({ networkError: String(e).slice(0, 160) }));

    const name = res.replace('/wm/', '');
    const rows = Array.isArray(r.body?.data) ? r.body.data : r.body?.data ? [r.body.data] : [];
    const rec = {
      ts: new Date().toISOString(), tool: 'tools/cdp/capture-read-shapes.mjs', case: 'read-shape',
      request: { method: 'GET', url: res, query: { query: '[]', offset: '0', limit: '2', siteId: 'SG', subsites: '----' }, headers: { accept: 'application/json' } },
      response: r.networkError ? { networkError: r.networkError }
        : { status: r.status, statusText: r.statusText, headers: strip(r.headers), body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
      notes: 'Issued in-page, so ambient headers are the browser\'s. Proves the body shape, not the header set — see SCHEMA.md.',
    };
    fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${name}.jsonl`), JSON.stringify(rec) + '\n');

    store.resources[name] = {
      path: res,
      status: r.status ?? null,
      kind: r.kind ?? 'ERROR',
      envelope_type: r.body?.['@type'] ?? null,
      rows_returned: rows.length,
      field_count: rows.length ? shapeOf(rows).length : 0,
      fields: rows.length ? shapeOf(rows) : [],
    };
    if (r.status === 200) ok++;
    process.stderr.write(`  [${i}/${targets.length}] ${name.padEnd(34)} ${r.status ?? 'ERR'} ${(r.kind ?? '').padEnd(14)} ${rows.length ? shapeOf(rows).length + ' fields' : ''}\n`);
    if (i % 20 === 0) fs.writeFileSync(OUT, JSON.stringify({ ...store, generated_by: 'tools/cdp/capture-read-shapes.mjs' }, null, 2) + '\n');
  }

  const all = Object.values(store.resources);
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-read-shapes.mjs',
    what_this_is: 'One recorded GET per collection resource: the response envelope, the field names it returns, their JSON types, and whether each was null in the sample. Every entry is backed by a stored exchange.',
    totals: { resources: all.length, ok: all.filter((x) => x.status === 200).length, distinct_fields: new Set(all.flatMap((x) => x.fields.map((f) => f.field))).size },
    resources: store.resources,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ probed: targets.length, ok, failed: targets.length - ok }, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
