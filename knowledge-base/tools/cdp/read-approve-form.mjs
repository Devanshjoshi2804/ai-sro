/*
 * read-approve-form.mjs — the second stage between clicking Approve and the request.
 *
 * The approval capture clicked Approve, a form appeared — "Approve Adjustments: Reason*, Comment,
 * Generate Cycle Count" — and the auto-confirm accepted its defaults before anyone read it. That
 * form is a decision point: `Generate Cycle Count` is a side effect, and `Reason` is required and
 * overrides what the adjustment already carries.
 *
 * This opens it and reads the field model, then CANCELS. It approves nothing. It is the same
 * read-only treatment every Add form in this base got, applied to an operational confirmation.
 *
 *   node tools/cdp/read-approve-form.mjs
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const OUT = `${KG}/index/operational-forms.json`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.inventory/wm.inventory.adjustments////';

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
/* If anything slips past the read-only intent, this records it rather than hiding it. */
const writes = [];
page.on('requestfinished', (req) => { if (req.method() !== 'GET' && /\/data\/WM\//.test(req.url())) writes.push(`${req.method()} ${req.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0]}`); });

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(16000);

  let frame = null;
  for (const fr of page.frames()) {
    const ok = await fr.evaluate(() => {
      if (!window.Ext) return false;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grid = window.Ext.ComponentQuery.query('grid').filter(vis).find((g) => g.getStore().getCount() > 0);
      if (!grid) return false;
      grid.getSelectionModel().select(0);   // any row: we are reading the form, not approving it
      return true;
    }).catch(() => false);
    if (ok) { frame = fr; break; }
  }
  if (!frame) { console.error('no populated approvals grid'); process.exit(1); }
  await page.waitForTimeout(1500);

  await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter(vis).find((x) => x.itemId === 'adjustments-approve');
    if (b && !b.disabled) { b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b); }
  });
  await page.waitForTimeout(5000);

  const form = await frame.evaluate(() => {
    if (!window.Ext) return null;
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
    if (!win) return null;
    const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
    return {
      title: clean(win.title),
      text: win.getEl && win.getEl() ? win.getEl().dom.innerText.replace(/\s+/g, ' ').trim().slice(0, 300) : '',
      fields: win.query('field').filter(vis).map((f) => ({
        field: f.name, label: clean(f.fieldLabel), type: f.xtype,
        required: f.allowBlank === false,
        value: f.getValue ? f.getValue() : undefined,
        options: f.getStore && f.getStore() && f.getStore().getCount && f.getStore().getCount() > 0 && f.getStore().getCount() <= 30
          ? f.getStore().getRange().map((r) => ({ v: r.get(f.valueField || 'code'), t: r.get(f.displayField || 'description') })) : undefined,
      })),
      buttons: win.query('button').filter(vis).map((b) => ({ text: clean(b.text), itemId: b.itemId, disabled: !!b.disabled })),
    };
  }).catch(() => null);

  console.log(JSON.stringify(form, null, 1)?.slice(0, 2000));
  await page.screenshot({ path: `${KG}/images/approve-adjustments-form.png` }).catch(() => {});

  /* Cancel. Nothing is approved by this tool. */
  const closed = await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
    if (!win) return 'no window';
    const cancel = win.query('button').find((b) => /^cancel$/i.test(String(b.text || '').trim()));
    if (cancel) { cancel.fireHandler ? cancel.fireHandler() : cancel.handler && cancel.handler.call(cancel.scope || cancel, cancel); return 'cancelled'; }
    win.close();
    return 'closed';
  }).catch(() => 'error');
  await page.waitForTimeout(3000);

  const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { forms: {} };
  store.generated_by = 'tools/cdp/read-approve-form.mjs';
  store.readOnly = 'the form is opened, read and cancelled; nothing is approved';
  store.forms['Adjustments > Approve'] = { ...form, closed_with: closed, writes_observed: writes };
  fs.writeFileSync(OUT, JSON.stringify(store, null, 2) + '\n');
  console.log(`\nclosed with: ${closed} · writes observed: ${writes.length ? writes.join(', ') : 'none'}`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
