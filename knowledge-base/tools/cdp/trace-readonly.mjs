/*
 * trace-readonly.mjs — trace Tier 2/3 operational screens WITHOUT writing anything.
 *
 * WHY READ-ONLY
 * These are transactional screens: Receiving, Shipping, Picking, Outbound Planner, Inventory, Yard.
 * A write here is not a throwaway config row — it can release a wave, confirm a receipt, or move
 * real inventory in a shared sandbox other people are using, and several of those have no clean
 * revert. The campaign plan says to stop rather than force a write with no reversal path, so this
 * tool deliberately cannot save: it never clicks Save and never invokes a doDelete/doCopy plugin.
 *
 * It still adds real graph edges, because a screen's READS are genuine structure: which resources
 * it depends on, in what order, and what each returns.
 *
 *   node tools/cdp/trace-readonly.mjs receiving
 *   node tools/cdp/trace-readonly.mjs all
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { appFrame, dismissBlocking } from './ext.mjs';

const OUT = 'knowlegde_graph/blue-yonder-sce/http/flows';

export const SCREENS = {
  receiving: '#wm.receiving/wm.receiving.dashboard////',
  shipping: '#wm.shipping/wm.shipping.dashboard////',
  picking: '#wm.picking/wm.outbounddashboard////',
  outboundPlanner: '#wm.outboundplanner/wm.outbounddashboard////',
  inventory: '#wm.inventory/wm.inventory.dashboard////',
  yard: '#wm.yard/wm.dooractivity////',
  systemAdmin: '#mcs-SystemAdmin/Deferred-Executions-2019-1-0////',
  specialPack: '#Special-Pack-rGOeUWX9SnSGderdweJ-og/Special-Pack-Operations////',
  operationsAdmin: '#Operations-Administration-E795TXjCR7K2DQpOMC0M4g/wm.config.warehouse.warehouse////',
};

/*
 * Hash routing only. A full page load drops this app's OIDC session, and these screens are the
 * expensive ones to get back to. Bounce through a neutral config route so the router always sees
 * a change even when the target hash is already current.
 */
async function goto(page, route) {
  await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
  await page.waitForTimeout(2200);
  await page.evaluate((h) => { window.location.hash = h; }, route);
  await page.waitForTimeout(7000);   // operational dashboards load far more than a config grid
  return appFrame(page);
}

/* Describe what is on screen without touching it. */
const describe = (page) => page.evaluate(() => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  if (!w.Ext) return { error: 'Ext not available' };
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const grids = w.Ext.ComponentQuery.query('grid').filter(vis).map((g) => ({
    cls: g.$className,
    rows: g.getStore ? g.getStore().getCount() : null,
    total: g.getStore && g.getStore().getTotalCount ? g.getStore().getTotalCount() : null,
    columns: (g.columns || []).slice(0, 8).map((c) => ({ text: c.text, dataIndex: c.dataIndex, xtype: c.xtype })),
  }));
  const forms = w.Ext.ComponentQuery.query('form').filter(vis).map((fm) => ({
    fields: fm.getForm().getFields().items.map((x) => ({
      field: x.name, label: x.fieldLabel, required: x.allowBlank === false, type: x.xtype,
    })).slice(0, 40),
  }));
  return {
    title: (document.title || '').slice(0, 60),
    grids, forms,
    // Buttons are recorded, never pressed: this is the inventory of what a writer would need.
    buttons: w.Ext.ComponentQuery.query('button').filter((b) => !b.isDestroyed && vis(b) && b.text)
      .map((b) => ({ text: String(b.text).replace(/<[^>]*>/g, '').slice(0, 40), itemId: b.itemId, disabled: !!b.disabled }))
      .slice(0, 30),
  };
});

async function trace(page, name) {
  const route = SCREENS[name];
  const out = { screen: name, route, readOnly: true, calls: [] };
  const pending = new Map();
  let seq = 0;
  const onReq = (req) => {
    if (!/\/data\//.test(req.url()) || /webPerformanceEntries/.test(req.url())) return;
    pending.set(req, { seq: seq++, method: req.method(), url: req.url().split('?')[0], query: req.url().split('?')[1] || null });
  };
  const onRes = async (res) => {
    const rec = pending.get(res.request());
    if (!rec) return;
    pending.delete(res.request());
    rec.status = res.status();
    try {
      const t = await res.text();
      rec.bytes = t.length;
      const j = JSON.parse(t);
      rec.rowCount = Array.isArray(j?.data) ? j.data.length : null;
      rec.sampleKeys = Array.isArray(j?.data) && j.data[0] ? Object.keys(j.data[0]).slice(0, 12) : null;
    } catch { /* non-JSON body */ }
    out.calls.push(rec);
  };
  page.on('request', onReq);
  page.on('response', onRes);
  try {
    await dismissBlocking(page);
    await goto(page, route);
    await page.waitForTimeout(3000);
    out.screenState = await describe(page);
    // Any non-GET seen here was fired by the app itself on load, not by us.
    out.writesObservedOnLoad = out.calls.filter((c) => c.method !== 'GET')
      .map((c) => `${c.method} ${c.url.split('/data/')[1]} -> ${c.status}`);
  } catch (e) {
    out.error = String(e).split('\n')[0].slice(0, 200);
  } finally {
    page.off('request', onReq);
    page.off('response', onRes);
  }
  out.calls.sort((a, b) => a.seq - b.seq);
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/readonly-${name}.json`, JSON.stringify(out, null, 2) + '\n');
  return out;
}

// Entry-guard: importing SCREENS must not kick off a trace run.
const isEntry = process.argv[1] && process.argv[1].endsWith('trace-readonly.mjs');
const arg = process.argv[2];
const names = !arg || arg === 'all' ? Object.keys(SCREENS) : [arg];
if (!isEntry) { /* imported for SCREENS only */ } else {
const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];
const summary = {};
for (const n of names) {
  const r = await trace(page, n);
  const resources = [...new Set(r.calls.map((c) => c.url.split('/data/')[1]).filter(Boolean))];
  summary[n] = {
    calls: r.calls.length,
    gets: r.calls.filter((c) => c.method === 'GET').length,
    writesOnLoad: r.writesObservedOnLoad || [],
    grids: r.screenState?.grids?.length ?? 0,
    forms: r.screenState?.forms?.length ?? 0,
    buttons: (r.screenState?.buttons || []).map((b) => b.text).slice(0, 10),
    distinctResources: resources.length,
    error: r.error,
  };
  process.stderr.write(`${n}: ${summary[n].calls} calls, ${summary[n].distinctResources} resources, grids ${summary[n].grids}${r.error ? ' ERR ' + r.error : ''}\n`);
}
console.log(JSON.stringify(summary, null, 1));
await browser.close();
}
