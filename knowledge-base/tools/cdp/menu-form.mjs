/*
 * menu-form.mjs — capture the Add-form model on screens whose create lives in an Actions menu.
 *
 * app-map.json marks the ten location screens `can_create:false`, which was only ever true of the
 * toolbar: `dump-actions-menu.mjs` found an enabled "Add" inside Actions on every one of them. So
 * the largest table in the system (61,912 rows) had no captured create payload for the same reason
 * `businessUnitDescription` was missing — nobody had opened the right control.
 *
 * Read-only: opens the menu, clicks Add, reads the field model, cancels.
 *
 *   node tools/cdp/menu-form.mjs "Storage Locations" "Dock Locations"
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const OUT = `${KG}/index/form-models-all.json`;

const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const targets = screens.filter((s) => process.argv.slice(2).includes(s.label));
if (!targets.length) { console.error('no matching screens'); process.exit(1); }

/*
 * Read the field model of whatever Add opened.
 *
 * Unlike the toolbar Add on Configuration screens, Actions > Add here opens a floating Ext
 * `window` that contains fields directly and has NO `form` component — which is why the first run
 * reported "no form rendered" on every location screen while a 7-field dialog was sitting open.
 * So: prefer a real form, fall back to the visible fields of the topmost window.
 */
const readForm = (fr) => fr.evaluate(() => {
  if (!window.Ext) return null;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
  const forms = window.Ext.ComponentQuery.query('form').filter(vis);
  const win = window.Ext.ComponentQuery.query('window').filter(vis).pop();
  const items = forms.length
    ? forms.sort((a, b) => b.getForm().getFields().items.length - a.getForm().getFields().items.length)[0].getForm().getFields().items
    : (win ? win.query('field').filter(vis) : []);
  if (!items || !items.length) return null;
  return (items.map ? items : items.items).map((x) => ({
    field: x.name, label: x.fieldLabel, required: x.allowBlank === false, type: x.xtype,
    maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
    options: x.getStore && x.getStore() && x.getStore().getCount && x.getStore().getCount() > 0 && x.getStore().getCount() <= 15
      ? x.getStore().getRange().map((r) => r.get(x.valueField || 'code')).filter(Boolean).slice(0, 15) : undefined,
  }));
}).catch(() => null);

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const store = JSON.parse(fs.readFileSync(OUT, 'utf8'));
const byHash = new Map(store.forms.map((f) => [f.hash, f]));

try {
  for (const t of targets) {
    const rec = { hash: t.hash, label: t.label, area: t.area, tier: t.tier, create_via: 'Actions menu > Add' };
    try {
      await page.goto(PORTAL + t.hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(12000);

      let opened = false;
      for (const fr of page.frames()) {
        const btn = await fr.evaluate(() => {
          if (!window.Ext) return null;
          const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
          const b = window.Ext.ComponentQuery.query('button')
            .filter((x) => !x.isDestroyed && vis(x) && (/actionsBtn$/i.test(x.itemId || '') || /^Actions$/i.test(x.text || ''))).pop();
          return b && b.getEl() ? b.getEl().dom.id : null;
        }).catch(() => null);
        if (!btn) continue;
        await fr.locator('#' + btn).click({ timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(1500);
        // Click the menu's Add by its own element id — menu items are not focusable by role here.
        const hit = await fr.evaluate(() => {
          if (!window.Ext) return null;
          const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
          const it = window.Ext.ComponentQuery.query('menu').filter(vis)
            .flatMap((m) => m.query('menuitem'))
            .filter((i) => !i.disabled && /^\s*Add\s*$/i.test(String(i.text || '').replace(/<[^>]*>/g, '')))[0];
          return it && it.getEl() ? it.getEl().dom.id : null;
        }).catch(() => null);
        if (hit) { await fr.locator('#' + hit).click({ timeout: 5000 }).catch(() => {}); opened = true; break; }
      }
      if (!opened) throw new Error('no enabled Add inside any Actions menu');
      await page.waitForTimeout(5000);

      let fields = null;
      for (const fr of page.frames()) { const r = await readForm(fr); if (r && r.length > (fields?.length || 0)) fields = r; }
      if (!fields) throw new Error('no form rendered after Actions > Add');
      rec.field_count = fields.length;
      rec.fields = fields;
      rec.required = fields.filter((f) => f.required);
    } catch (e) {
      rec.error = String(e).split('\n')[0].slice(0, 140);
    }
    byHash.set(t.hash, rec);
    console.log(`${t.label}: ${rec.error ? 'ERR ' + rec.error : `${rec.field_count} fields, ${rec.required.length} required`}`);
    if (rec.required) console.log('  required: ' + rec.required.map((f) => `${f.field}(${f.type})`).join(', '));
  }
  fs.writeFileSync(OUT, JSON.stringify({ ...store, forms: [...byHash.values()] }, null, 2) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
