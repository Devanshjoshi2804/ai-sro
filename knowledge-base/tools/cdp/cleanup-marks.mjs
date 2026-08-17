/*
 * cleanup-marks.mjs — find and remove throwaway records a battery created but could not delete.
 *
 * Three resources answered a create with `201` and an EMPTY BODY: no `resourceId`, nothing to
 * address the new record by. The battery had nothing to delete, so it left real rows behind —
 * `itemClasses`, `itemStyleAttributes`, `workOperations`. This finds them by their ZV marker,
 * reads the `resourceId` the COLLECTION reports, deletes, and proves each one gone.
 *
 * The collection read is paged deliberately: an unpaged read has produced a false "nothing left"
 * here before.
 *
 *   node tools/cdp/cleanup-marks.mjs itemClasses itemStyleAttributes workOperations
 *   node tools/cdp/cleanup-marks.mjs --scan <resource>     find only, delete nothing
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const HTTP_DIR = 'knowlegde_graph/blue-yonder-sce/http';
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const MARK = /ZV\d{3,6}/;

const call = (page, method, urlPath, body) => page.evaluate(
  async ({ method, urlPath, body, base }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;
    let res, text = '';
    try { res = await w.fetch(base + urlPath, { method, credentials: 'include', headers, body: body ? JSON.stringify(body) : undefined }); text = await res.text(); }
    catch (e) { return { networkError: String(e).slice(0, 160) }; }
    let parsed = null; try { parsed = JSON.parse(text); } catch {}
    let kind = 'OK';
    if (res.status === 404) kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
    return { status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 400), kind };
  }, { method, urlPath, body, base: BASE });

const scanOnly = process.argv.includes('--scan');
const resources = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!resources.length) { console.error('usage: cleanup-marks.mjs [--scan] <resource>...'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  for (const res of resources) {
    const hits = [];
    for (let offset = 0; offset < 4000; offset += 200) {
      const r = await call(page, 'GET', `/wm/${res}?query=[]&offset=${offset}&limit=200&siteId=SG&subsites=----`);
      const rows = Array.isArray(r.body?.data) ? r.body.data : [];
      for (const row of rows) if (MARK.test(JSON.stringify(row))) hits.push(row);
      if (rows.length < 200) break;                 // last page
    }
    console.log(`\n${res}: ${hits.length} marked row(s)`);
    for (const h of hits) {
      const id = h.resourceId;
      console.log(`  ${id}  ${JSON.stringify(h).slice(0, 120)}`);
      if (scanOnly || !id) continue;
      const idPath = `/wm/${res}/${encodeURIComponent(id)}`;
      const del = await call(page, 'DELETE', idPath);
      const gone = await call(page, 'GET', idPath);
      for (const [name, x] of [['cleanup-delete', del], ['cleanup-confirm-gone', gone]]) {
        fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${res}.jsonl`), JSON.stringify({
          ts: new Date().toISOString(), tool: 'tools/cdp/cleanup-marks.mjs', case: name,
          request: { method: name.includes('delete') ? 'DELETE' : 'GET', url: `/wm/${res}/{id}`, headers: { accept: 'application/json' } },
          response: { status: x.status, body: x.body, bodyRaw: x.bodyRaw, kind: x.kind },
          notes: 'Removing a record a battery created but could not address: the 201 carried an empty body, so no resourceId was returned at create time.',
        }) + '\n');
      }
      console.log(`    delete ${del.status} · confirm ${gone.status} ${gone.kind}`);
    }
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
