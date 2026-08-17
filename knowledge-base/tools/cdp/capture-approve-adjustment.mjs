/*
 * capture-approve-adjustment.mjs — capture what "Approve" sends on Inventory ▸ Adjustments.
 *
 * This is a REAL operational write: approving an inventory adjustment moves stock, and there is no
 * Unapprove. It is run once, against one named row, with the user's explicit approval.
 *
 * The target is deliberately the adjustment this project's own L1 run created on 2026-08-13 —
 * LPN 00000776442003826960, item 0113224000, location EF131, 66 CS -> 65 CS, reason AA. Approving it
 * completes work we started rather than touching somebody else's pending count.
 *
 * The point is the request. The one operational write ever observed here answered 200 with
 * `approvalRequired: true` and moved nothing, so the effect of an approval is unknown until the
 * before and after are both recorded — which this does, on the queue and on the inventory itself.
 *
 *   node tools/cdp/capture-approve-adjustment.mjs 00000776442003826960
 *   node tools/cdp/capture-approve-adjustment.mjs 00000776442003826960 --dry
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/http/flows/approveAdjustment.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.inventory/wm.inventory.adjustments////';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

const LPN = process.argv[2];
const dry = process.argv.includes('--dry');
if (!LPN) { console.error('usage: capture-approve-adjustment.mjs <lpn> [--dry]'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

const api = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  const r = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } });
  const t = await r.text();
  let j = null; try { j = JSON.parse(t); } catch {}
  return { status: r.status, body: j, sessionExpired: !j && /b2clogin|<html/i.test(t) };
}, { url, base: BASE });

const captured = [];
page.on('requestfinished', async (req) => {
  if (req.method() === 'GET' || !/\/data\/WM\//.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null; try { body = await res?.json(); } catch {}
  captured.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, '').split('&_dc')[0],
    request_headers: strip(req.headers()),
    request_body: (() => { try { return JSON.parse(req.postData() || 'null'); } catch { return req.postData()?.slice(0, 3000) ?? null; } })(),
    status: res?.status(), response_body: body,
  });
});

const invQuery = encodeURIComponent(JSON.stringify([{ column: 'lpn', operator: 'EQ', value: LPN }]));
const snapshot = async () => {
  const q = await api('/wm/inventoryAdjustmentApprovals?query=[]&offset=0&limit=50&siteId=SG&subsites=----');
  const inv = await api(`/wm/structuredInventory?query=${invQuery}&offset=0&limit=10&siteId=SG&subsites=----`);
  const rows = q.body?.data ?? [];
  return {
    approvals_pending: rows.length,
    our_row: rows.find((r) => String(r.lpn) === LPN) ? 'still queued' : 'not in queue',
    inventory: (inv.body?.data ?? []).map((r) => ({ item: r.itemNumber, quantity: r.unitQuantity, status: r.inventoryStatus, location: r.location })),
  };
};

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(16000);

  const before = await snapshot();
  console.log('BEFORE:', JSON.stringify(before));
  if (before.our_row !== 'still queued') { console.error('the target row is not in the queue — nothing to approve'); process.exit(1); }

  /* Select the row by LPN, then read back what the grid thinks is selected before acting. */
  let frame = null;
  for (const fr of page.frames()) {
    const r = await fr.evaluate((lpn) => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grid = window.Ext.ComponentQuery.query('grid').filter(vis)
        .find((g) => g.getStore().findBy((rec) => String(rec.get('lpn')) === lpn) >= 0);
      if (!grid) return null;
      const idx = grid.getStore().findBy((rec) => String(rec.get('lpn')) === lpn);
      grid.getSelectionModel().select(idx);
      const sel = grid.getSelectionModel().getSelection().map((r) => ({ lpn: r.get('lpn'), item: r.get('itemNumber'), rowId: r.get('rowId'), adjustmentQuantity: r.get('adjustmentQuantity') }));
      return { rows: grid.getStore().getCount(), selected: sel };
    }, LPN).catch(() => null);
    if (r) { frame = fr; console.log('selected:', JSON.stringify(r.selected)); break; }
  }
  if (!frame) { console.error('could not find the approvals grid'); process.exit(1); }
  await page.waitForTimeout(1500);

  const btn = await frame.evaluate(() => {
    if (!window.Ext) return null;
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => x.itemId === 'adjustments-approve');
    return b ? { found: true, enabled: !b.disabled } : null;
  });
  console.log('approve button:', JSON.stringify(btn));
  if (!btn?.found) { console.error('no approve button'); process.exit(1); }
  if (dry) { console.log('\n--dry: stopping before the write. Nothing was approved.'); process.exit(0); }
  if (!btn.enabled) { console.error('approve is disabled even with a row selected — stopping'); process.exit(1); }

  captured.length = 0;
  await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => x.itemId === 'adjustments-approve');
    b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
  });
  await page.waitForTimeout(6000);
  await page.screenshot({ path: `${KG}/images/approve-adjustment-after-click.png` }).catch(() => {});

  /* Confirm whatever dialog it raises — an approval usually asks. */
  const modal = await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('messagebox,window').filter(vis).pop();
    if (!win) return 'no modal';
    const el = win.getEl && win.getEl() && win.getEl().dom;
    const text = el ? el.innerText.replace(/\s+/g, ' ').trim().slice(0, 300) : '';
    const yes = win.query('button').find((b) => /^(yes|ok|approve|confirm)$/i.test(String(b.text || '').trim()));
    if (yes) { yes.fireHandler ? yes.fireHandler() : yes.handler && yes.handler.call(yes.scope || yes, yes); return `confirmed :: ${text}`; }
    return `modal with no confirm button :: ${text}`;
  }).catch(() => 'error reading modal');
  console.log('modal:', modal);
  await page.waitForTimeout(8000);

  console.log(`\nrequests the click produced (${captured.length}):`);
  for (const c of captured) console.log(`  ${c.method} ${c.url} -> ${c.status}`);

  const after = await snapshot();
  console.log('\nAFTER:', JSON.stringify(after));

  for (const c of captured) {
    const resource = (c.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1] || 'inventoryAdjustmentApprovals';
    fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/capture-approve-adjustment.mjs',
      case: c.status >= 200 && c.status < 300 ? 'approve-adjustment' : `approve-adjustment-${c.status}`,
      request: { method: c.method, url: c.url.replace('/data/WM', '').split('?')[0], query: Object.fromEntries(new URLSearchParams(c.url.split('?')[1] || '')), headers: c.request_headers, body: c.request_body },
      response: { status: c.status, body: c.response_body },
      notes: `Approving a pending inventory adjustment through the UI. Target LPN ${LPN}, the row this project's own L1 run created. Before: ${JSON.stringify(before)} After: ${JSON.stringify(after)}`,
    }) + '\n');
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-approve-adjustment.mjs',
    what_this_is: 'The first operational APPROVAL captured on this instance: Inventory > Adjustments > Approve, driven through the UI, with the queue and the inventory read before and after.',
    target: { lpn: LPN, note: 'the adjustment this project\'s own L1 run created on 2026-08-13' },
    before, after, modal, requests: captured,
  }, null, 2) + '\n');
  console.log(`\nflow written to ${OUT}`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
