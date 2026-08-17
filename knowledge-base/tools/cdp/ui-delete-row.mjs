/*
 * ui-delete-row.mjs — delete a row through the UI, recording every request the click produces.
 *
 * WHY: `DELETE /wm/workOperations/ZV614*!SG` answers **200 with an empty body and does not delete**.
 * Repeated four times, three id spellings, with and without site params — the record survives every
 * one. That is a resource whose API delete silently no-ops, and it left a throwaway row behind.
 *
 * So drive the screen the way an operator would and watch the wire: either the UI calls something
 * different, or it calls the same thing and fails the same way — and both answers are worth having,
 * because one of them means the row can only be removed by hand.
 *
 *   node tools/cdp/ui-delete-row.mjs "Work Operations" ZV614
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const [label, marker] = process.argv.slice(2);
if (!label || !marker) { console.error('usage: ui-delete-row.mjs "<screen>" <marker>'); process.exit(1); }

const screen = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens.find((s) => s.label === label);
if (!screen) { console.error('no such screen'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const seen = [];
page.on('requestfinished', async (req) => {
  if (!/\/data\/WM\//.test(req.url()) || req.method() === 'GET') return;
  const res = await req.response();
  seen.push({ method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, ''), status: res?.status(), body: req.postData()?.slice(0, 400) });
});

try {
  await page.goto(PORTAL + screen.hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);

  /* Find the row by its marker and tick its row-checker; the toolbar Delete stays disabled until then. */
  const picked = await (async () => {
    for (const fr of page.frames()) {
      const r = await fr.evaluate((mark) => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const grid = window.Ext.ComponentQuery.query('grid').filter(vis)[0];
        if (!grid) return null;
        const idx = grid.getStore().findBy((rec) => JSON.stringify(rec.data).includes(mark));
        if (idx < 0) return { found: false, rows: grid.getStore().getCount() };
        grid.getSelectionModel().select(idx);
        return { found: true, idx, data: grid.getStore().getAt(idx).data };
      }, marker).catch(() => null);
      if (r) return { frame: fr, ...r };
    }
    return null;
  })();
  if (!picked || !picked.found) { console.log('row not found on the first page of the grid', picked); process.exit(1); }
  console.log(`selected row ${picked.idx}`);
  await page.waitForTimeout(1500);

  const clicked = await picked.frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter((x) => x.itemId === 'deleteButton' && vis(x))[0];
    if (!b || b.disabled) return { ok: false, disabled: b ? b.disabled : 'no button' };
    b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
    return { ok: true };
  });
  console.log('delete clicked:', JSON.stringify(clicked));
  await page.waitForTimeout(2500);

  /* Confirm any modal the app raises. */
  const confirmed = await picked.frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('messagebox,window').filter(vis).pop();
    if (!win) return 'no modal';
    const btn = win.query('button').filter((b) => /^(yes|ok|delete|confirm)$/i.test(String(b.text || '').trim()))[0];
    if (!btn) return 'modal with no confirm button: ' + win.query('button').map((b) => b.text).join(',');
    btn.fireHandler ? btn.fireHandler() : btn.handler && btn.handler.call(btn.scope || btn, btn);
    return 'confirmed';
  }).catch(() => 'error');
  console.log('modal:', confirmed);
  await page.waitForTimeout(5000);

  console.log(`\nrequests the click produced (${seen.length}):`);
  for (const s of seen) console.log(`  ${s.method} ${s.url} -> ${s.status}${s.body ? ' body=' + s.body.slice(0, 120) : ''}`);

  fs.appendFileSync(path.join(KG, 'http', 'ui-actions.jsonl'), JSON.stringify({
    ts: new Date().toISOString(), tool: 'tools/cdp/ui-delete-row.mjs', screen: label, marker,
    selected_row: picked.data, delete_clicked: clicked, modal: confirmed, requests: seen,
  }) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
