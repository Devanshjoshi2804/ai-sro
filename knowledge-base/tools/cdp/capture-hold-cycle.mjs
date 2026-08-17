/*
 * capture-hold-cycle.mjs — capture two operational writes that undo each other.
 *
 * Apply Hold and Release Hold are the safest real writes in this system: they are a matched pair, the
 * inventory quantity never changes, and the second one reverses the first. That makes them the right
 * place to learn what an operational write actually sends, before anything irreversible is attempted.
 *
 * The cycle is: read the LPN's state, apply a hold, record the request, release it, record that
 * request, then read the state again and prove it came back. If the release fails, the run says so
 * loudly rather than finishing quietly — a held LPN cannot be picked, so a hold left behind is a real
 * operational consequence.
 *
 *   node tools/cdp/capture-hold-cycle.mjs --dry
 *   node tools/cdp/capture-hold-cycle.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/http/flows/holdCycle.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.inventory/wm.inventorydisplay////';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const TELEMETRY = /webPerformanceEntries|rpux\/persistence|serverStatus/;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));
const dry = process.argv.includes('--dry');
/* The LPN this project already adjusted, so the blast radius stays on inventory we have touched. */
const PREFERRED_LPN = process.argv.find((a) => /^\d{15,}$/.test(a)) || '00000776442003826960';

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

let bucket = [];
page.on('requestfinished', async (req) => {
  if (req.method() === 'GET' || !/\/data\/WM\//.test(req.url()) || TELEMETRY.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null; try { body = await res?.json(); } catch {}
  bucket.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, '').split('&_dc')[0],
    request_headers: strip(req.headers()),
    request_body: (() => { try { return JSON.parse(req.postData() || 'null'); } catch { return req.postData()?.slice(0, 3000) ?? null; } })(),
    status: res?.status(), response_body: body,
  });
});

const api = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  const r = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } });
  const t = await r.text();
  let j = null; try { j = JSON.parse(t); } catch {}
  return { status: r.status, body: j, sessionExpired: !j && /b2clogin|<html/i.test(t) };
}, { url, base: BASE });

/* State of the LPN: its inventory row, and how many hold-history entries exist for it. */
const stateOf = async (lpn) => {
  const q = encodeURIComponent(JSON.stringify([{ column: 'lpn', operator: 'EQ', value: lpn }]));
  const inv = await api(`/wm/structuredInventory?query=${q}&offset=0&limit=5&siteId=SG&subsites=----`);
  const hist = await api(`/wm/holdsHistory?query=${q}&offset=0&limit=50&siteId=SG&subsites=----`);
  return {
    inventory: (inv.body?.data ?? []).map((r) => ({ item: r.itemNumber, quantity: r.unitQuantity, status: r.inventoryStatus, holdFlag: r.holdFlag ?? r.onHoldFlag ?? null })),
    hold_history_rows: Array.isArray(hist.body?.data) ? hist.body.data.length : null,
  };
};

const inFrame = (frame, fn, arg) => frame.evaluate(fn, arg);

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(16000);

  /* Find the grid and pick the row: our own LPN if it is on the page, otherwise the first row. */
  let frame = null, picked = null;
  for (const fr of page.frames()) {
    const r = await inFrame(fr, (want) => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grid = window.Ext.ComponentQuery.query('grid').filter(vis).find((g) => g.getStore().getCount() > 0);
      if (!grid) return null;
      const st = grid.getStore();
      let idx = st.findBy((rec) => String(rec.get('lpn')) === want);
      const usedPreferred = idx >= 0;
      if (idx < 0) idx = 0;
      grid.getSelectionModel().select(idx);
      const rec = st.getAt(idx);
      return { usedPreferred, rows: st.getCount(), lpn: String(rec.get('lpn')), item: rec.get('itemNumber'), qty: rec.get('unitQuantity'), status: rec.get('inventoryStatus') };
    }, PREFERRED_LPN).catch(() => null);
    if (r) { frame = fr; picked = r; break; }
  }
  if (!frame) { console.error('no populated inventory grid'); process.exit(1); }
  console.log(`grid rows ${picked.rows} · selected ${picked.usedPreferred ? 'OUR LPN' : 'first row'}: ${picked.lpn} item ${picked.item} qty ${picked.qty} status ${picked.status}`);

  const before = await stateOf(picked.lpn);
  console.log('BEFORE:', JSON.stringify(before));

  /* Open Apply Hold and read what it offers. */
  const openAction = async (text) => {
    await inFrame(frame, () => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const b = window.Ext.ComponentQuery.query('button').filter(vis)
        .find((x) => /actionsBtn$/i.test(x.itemId || '') || /^Actions$/i.test(String(x.text || '').trim()));
      if (b && b.menu && b.showMenu) b.showMenu();
    });
    await page.waitForTimeout(2500);
    for (let i = 0; i < 6; i++) {
      const ok = await inFrame(frame, (t) => {
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
        const it = window.Ext.ComponentQuery.query('menu').filter(vis).flatMap((m) => m.query('menuitem'))
          .find((x) => !x.disabled && clean(x.text) === t);
        if (!it) return false;
        it.fireHandler ? it.fireHandler() : it.handler && it.handler.call(it.scope || it, it);
        return true;
      }, text).catch(() => false);
      if (ok) return true;
      await page.waitForTimeout(2000);
    }
    return false;
  };

  if (!await openAction('Apply Hold')) { console.error('could not open Apply Hold'); process.exit(1); }
  await page.waitForTimeout(5000);

  const holdPanel = await inFrame(frame, () => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    const grids = window.Ext.ComponentQuery.query('grid').filter(vis);
    // The panel lists hold definitions to choose from; take the first selectable one.
    const holdGrid = grids.find((g) => (g.columns || []).some((c) => /hold/i.test(c.dataIndex || '')));
    const first = holdGrid && holdGrid.getStore().getCount() ? holdGrid.getStore().getAt(0).data : null;
    if (holdGrid && first) holdGrid.getSelectionModel().select(0);
    return {
      hold_grid_rows: holdGrid ? holdGrid.getStore().getCount() : 0,
      chosen_hold: first ? { holdType: first.holdType ?? first.holdNumber, description: first.holdTypeDescription ?? first.longDescription } : null,
      buttons: window.Ext.ComponentQuery.query('button').filter(vis).map((b) => clean(b.text)).filter(Boolean).slice(0, 12),
    };
  }).catch(() => null);
  console.log('apply-hold panel:', JSON.stringify(holdPanel));

  if (dry) {
    await inFrame(frame, () => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => /^cancel$/i.test(String(x.text || '').trim()));
      if (b) b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
    }).catch(() => {});
    console.log('\n--dry: cancelled before applying. Nothing was written.');
    process.exit(0);
  }

  /* APPLY */
  bucket = [];
  await inFrame(frame, () => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => /^apply$/i.test(String(x.text || '').trim()));
    if (b) b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
  });
  await page.waitForTimeout(7000);
  const applyRequests = bucket.slice();
  console.log(`\nAPPLY produced ${applyRequests.length} request(s):`);
  for (const r of applyRequests) console.log(`  ${r.method} ${r.url} -> ${r.status}`);
  const afterApply = await stateOf(picked.lpn);
  console.log('AFTER APPLY:', JSON.stringify(afterApply));

  /* RELEASE — always attempted, even if the apply looked unclear. */
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(15000);
  for (const fr of page.frames()) {
    const ok = await inFrame(fr, (want) => {
      if (!window.Ext) return false;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grid = window.Ext.ComponentQuery.query('grid').filter(vis).find((g) => g.getStore().getCount() > 0);
      if (!grid) return false;
      let idx = grid.getStore().findBy((rec) => String(rec.get('lpn')) === want);
      if (idx < 0) return false;
      grid.getSelectionModel().select(idx);
      return true;
    }, picked.lpn).catch(() => false);
    if (ok) { frame = fr; break; }
  }
  bucket = [];
  const released = await openAction('Release Hold');
  await page.waitForTimeout(5000);
  if (released) {
    await inFrame(frame, () => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grids = window.Ext.ComponentQuery.query('grid').filter(vis);
      const g = grids.find((x) => x.getStore().getCount() > 0);
      if (g) g.getSelectionModel().select(0);
      const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => /^(release|apply|ok)$/i.test(String(x.text || '').trim()));
      if (b) b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
    }).catch(() => {});
    await page.waitForTimeout(7000);
  }
  const releaseRequests = bucket.slice();
  console.log(`\nRELEASE produced ${releaseRequests.length} request(s):`);
  for (const r of releaseRequests) console.log(`  ${r.method} ${r.url} -> ${r.status}`);
  const after = await stateOf(picked.lpn);
  console.log('AFTER RELEASE:', JSON.stringify(after));

  for (const [phase, reqs] of [['apply-hold', applyRequests], ['release-hold', releaseRequests]]) {
    for (const r of reqs) {
      const resource = (r.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1] || 'inventory';
      fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
        ts: new Date().toISOString(), tool: 'tools/cdp/capture-hold-cycle.mjs', case: phase,
        request: { method: r.method, url: r.url.replace('/data/WM', '').split('?')[0], query: Object.fromEntries(new URLSearchParams(r.url.split('?')[1] || '')), headers: r.request_headers, body: r.request_body },
        response: { status: r.status, body: r.response_body },
        notes: `${phase} on LPN ${picked.lpn} through the UI. Hold and release are a reversible pair; quantity is untouched.`,
      }) + '\n');
    }
  }
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-hold-cycle.mjs',
    lpn: picked.lpn, selected: picked, hold_panel: holdPanel,
    before, after_apply: afterApply, after_release: after,
    apply_requests: applyRequests, release_requests: releaseRequests,
    reversed: JSON.stringify(before.inventory) === JSON.stringify(after.inventory),
  }, null, 2) + '\n');
  console.log(`\nreversed cleanly: ${JSON.stringify(before.inventory) === JSON.stringify(after.inventory)}`);
  if (!releaseRequests.length && applyRequests.length) console.error('\n!! A HOLD MAY STILL BE APPLIED — release produced no request. Check Holds on this LPN.');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
