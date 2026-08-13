/*
 * trace-subroutes.mjs — read-only trace of every Tier 2/3 sub-route.
 *
 * STRICTLY READ-ONLY: navigates and records what each screen loads. It never clicks Save, never
 * invokes a grid-action plugin, and never submits a form. These screens move real inventory and
 * release real work in a shared environment, and several actions have no clean revert.
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';

const ROUTES = JSON.parse(fs.readFileSync('tools/cdp/tier2-routes.json', 'utf8'));
const OUT = 'knowlegde_graph/blue-yonder-sce/http/flows';
const area = process.argv[2];
const areas = area ? { [area]: ROUTES[area] } : ROUTES;

const browser = await chromium.connectOverCDP('http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];

const results = [];
for (const [a, list] of Object.entries(areas)) {
  for (const r of list) {
    const rec = { area: a, label: r.text, route: r.href, calls: [] };
    const pending = new Map();
    let seq = 0;
    const onReq = (q) => {
      if (!/\/data\//.test(q.url()) || /webPerformanceEntries/.test(q.url())) return;
      pending.set(q, { seq: seq++, method: q.method(), url: q.url().split('?')[0] });
    };
    const onRes = async (s) => {
      const c = pending.get(s.request());
      if (!c) return;
      pending.delete(s.request());
      c.status = s.status();
      try { const j = JSON.parse(await s.text()); c.rowCount = Array.isArray(j?.data) ? j.data.length : null; } catch {}
      rec.calls.push(c);
    };
    page.on('request', onReq); page.on('response', onRes);
    try {
      await dismissBlocking(page);
      await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
      await page.waitForTimeout(1500);
      await page.evaluate((h) => { window.location.hash = h; }, r.href);
      await page.waitForTimeout(5000);
      rec.state = await page.evaluate(() => {
        const w = document.querySelector('iframe')?.contentWindow;
        if (!w || !w.Ext) return { error: 'no Ext' };
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        return {
          grids: w.Ext.ComponentQuery.query('grid').filter(vis).map((g) => ({
            rows: g.getStore ? g.getStore().getCount() : null,
            total: g.getStore?.().getTotalCount ? g.getStore().getTotalCount() : null,
            cols: (g.columns || []).slice(0, 6).map((c) => c.dataIndex).filter(Boolean),
          })),
          // Recorded, never pressed — this is the inventory of actions a future writer would need.
          actions: w.Ext.ComponentQuery.query('button').filter((b) => !b.isDestroyed && vis(b) && b.text)
            .map((b) => String(b.text).replace(/<[^>]*>/g, '').trim().slice(0, 30)).filter(Boolean).slice(0, 12),
        };
      });
    } catch (e) { rec.error = String(e).split('\n')[0].slice(0, 140); }
    page.off('request', onReq); page.off('response', onRes);
    rec.calls.sort((x, y) => x.seq - y.seq);
    rec.writesOnLoad = rec.calls.filter((c) => c.method !== 'GET').map((c) => `${c.method} ${c.url.split('/data/')[1]}`);
    results.push(rec);
    process.stderr.write(`${a}/${r.text}: ${rec.calls.length} calls, grids ${rec.state?.grids?.length ?? 0}${rec.error ? ' ERR' : ''}\n`);
  }
}
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(`${OUT}/readonly-subroutes${area ? '-' + area : ''}.json`, JSON.stringify({ readOnly: true, results }, null, 2) + '\n');
const resources = new Set();
results.forEach((r) => r.calls.forEach((c) => { const m = /\/data\/WM\/wm\/([^/]+)/.exec(c.url); if (m) resources.add(m[1]); }));
console.log(JSON.stringify({
  routesTraced: results.length,
  withGrids: results.filter((r) => (r.state?.grids?.length ?? 0) > 0).length,
  errors: results.filter((r) => r.error).length,
  writesObservedOnLoad: results.flatMap((r) => r.writesOnLoad),
  distinctWmResources: [...resources].sort(),
}, null, 1));
await browser.close();
