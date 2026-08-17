/*
 * capture-subresources.mjs — record the sub-resource endpoints nothing has ever called.
 *
 * The catalogue lists 72 endpoints of the form `/wm/<resource>/<sub>` — `/nonpaged`, `/count`,
 * `/paged`, and named ones like `/carrierMatrices/carrierGroups`. Sixty-one of them have never been
 * called by this capture: every probe so far went to the collection or to a record by id. They are
 * the largest untouched slice of the API surface left.
 *
 * All GETs, recorded with whatever comes back — a 400 for a missing parameter is as much a fact
 * about the contract as a 200.
 *
 *   node tools/cdp/capture-subresources.mjs --dry
 *   node tools/cdp/capture-subresources.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/sub-resources.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';

const eps = (() => { const e = JSON.parse(fs.readFileSync(`${KG}/index/api-endpoints.json`, 'utf8')); return Array.isArray(e) ? e : e.endpoints; })();
/*
 * Default: the `/wm/<resource>/<sub>` endpoints. With `--commands`, the other untouched WM slice —
 * the 23 RPC-shaped `list*` calls and the handful of bare `/wm/<x>` paths nothing has hit. Left out
 * deliberately: `/data/WM/rpux/*` and `/refs/pageBuilder/*`, which are grid-column and page-layout
 * plumbing for the UI rather than warehouse data.
 */
const commandMode = process.argv.includes('--commands');
const subs = eps.filter((e) => commandMode
  ? /^\/data\/WM\/(?!rpux|wm\/[A-Za-z0-9]+\/)/.test(e.path)
  : /^\/data\/WM\/wm\/[A-Za-z0-9]+\/[A-Za-z0-9]+$/.test(e.path))
  .map((e) => e.path.replace('/data/WM', ''));

/* Which have already been recorded, by exact path. */
const seen = new Set();
for (const f of fs.readdirSync(EX)) {
  for (const l of fs.readFileSync(path.join(EX, f), 'utf8').split('\n').filter(Boolean)) {
    try { const r = JSON.parse(l); if (r.request?.url) seen.add(r.request.url); } catch {}
  }
}
const targets = [...new Set(subs)].filter((p) => !seen.has(p));
console.log(`${subs.length} sub-resource endpoints catalogued, ${targets.length} never called`);
if (process.argv.includes('--dry')) { console.log(targets.join('\n')); process.exit(0); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const store = { generated_by: 'tools/cdp/capture-subresources.mjs', endpoints: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  let i = 0;
  for (const p of targets) {
    i++;
    const url = `${p}?query=[]&offset=0&limit=2&siteId=SG&subsites=----`;
    const r = await page.evaluate(async ({ url, base }) => {
      const f = document.querySelector('iframe');
      const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
      let res, text = '';
      try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
      catch (e) { return { networkError: String(e).slice(0, 120) }; }
      let parsed = null; try { parsed = JSON.parse(text); } catch {}
      let kind = 'OK';
      if (res.status === 404) kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
      else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
      return { status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 400), kind };
    }, { url, base: BASE }).catch((e) => ({ networkError: String(e).slice(0, 120) }));

    const resource = p.split('/')[2] || p.replace(/^\//, '');
    const data = r.body?.data;
    const rows = Array.isArray(data) ? data : data ? [data] : [];
    const rec = {
      ts: new Date().toISOString(), tool: 'tools/cdp/capture-subresources.mjs', case: 'sub-resource-read',
      request: { method: 'GET', url: p, query: { limit: '2', siteId: 'SG', subsites: '----' }, headers: { accept: 'application/json' } },
      response: r.networkError ? { networkError: r.networkError }
        : { status: r.status, body: rows.length > 2 ? { ...r.body, data: rows.slice(0, 2) } : r.body, bodyRaw: r.bodyRaw, kind: r.kind },
      notes: 'A sub-resource endpoint from the catalogue that no probe had ever called.',
    };
    if (rows.length > 2) rec.response.body_truncated = { rows_returned: rows.length, rows_kept: 2 };
    fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify(rec) + '\n');

    store.endpoints[p] = {
      status: r.status ?? null, kind: r.kind ?? 'ERROR', rows: rows.length,
      fields: rows[0] && typeof rows[0] === 'object' ? Object.keys(rows[0]).length : 0,
      error: (r.body?.errors || []).map((e) => e.userMessage).join('; ') || undefined,
    };
    process.stderr.write(`  [${i}/${targets.length}] ${p.padEnd(52)} ${r.status ?? 'ERR'} ${(r.kind ?? '').padEnd(12)} ${rows.length ? rows.length + ' rows' : ''}\n`);
    if (i % 15 === 0) fs.writeFileSync(OUT, JSON.stringify(store, null, 2) + '\n');
  }

  const all = Object.values(store.endpoints);
  store.totals = {
    probed: all.length,
    ok: all.filter((x) => x.status === 200).length,
    needs_a_parameter: all.filter((x) => x.status === 400 || x.status === 422).length,
    not_a_route: all.filter((x) => x.kind === 'ROUTE-MISSING').length,
  };
  fs.writeFileSync(OUT, JSON.stringify(store, null, 2) + '\n');
  console.log(JSON.stringify(store.totals, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
