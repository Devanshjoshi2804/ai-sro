/*
 * walk-wizard.mjs — step through a multi-step Add dialog, recording the field model at each step.
 *
 * Actions > Add on the location screens does not open a form; it opens a WIZARD. The first capture
 * saw only its step-2 control ("2. Select a location type", a combo of six type codes), which means
 * the create payload for the 61,912-row locations table is not one field model but one per chosen
 * location type. A single readForm() can never see it.
 *
 * This walks forward: read the visible fields and buttons, pick the first option of any required
 * combo, click Next, repeat — then Cancel. It never clicks Finish/Save, so nothing is created.
 *
 *   node tools/cdp/walk-wizard.mjs "Storage Locations"
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const OUT = `${KG}/index/wizards.json`;
const MAX_STEPS = 6;

const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const targets = screens.filter((s) => process.argv.slice(2).includes(s.label));
if (!targets.length) { console.error('no matching screens'); process.exit(1); }

/* Everything below runs inside one frame; the wizard lives entirely in the screen's own frame. */
const snapshot = (fr) => fr.evaluate(() => {
  if (!window.Ext) return null;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
  const win = window.Ext.ComponentQuery.query('window').filter(vis).pop();
  if (!win) return null;
  return {
    title: String(win.title || '').replace(/<[^>]*>/g, '').trim(),
    fields: win.query('field').filter(vis).map((x) => ({
      field: x.name, label: String(x.fieldLabel || '').replace(/<[^>]*>/g, '').trim(),
      required: x.allowBlank === false, type: x.xtype,
      maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
      value: x.getValue ? x.getValue() : undefined,
      options: x.getStore && x.getStore() && x.getStore().getCount && x.getStore().getCount() > 0 && x.getStore().getCount() <= 20
        ? x.getStore().getRange().map((r) => ({ v: r.get(x.valueField || 'code'), t: r.get(x.displayField || 'description') })) : undefined,
    })),
    buttons: win.query('button').filter(vis).map((b) => ({ text: String(b.text || '').replace(/<[^>]*>/g, '').trim(), itemId: b.itemId, disabled: !!b.disabled, dom: b.getEl() && b.getEl().dom.id })),
  };
});

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const out = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { wizards: {} };

try {
  for (const t of targets) {
    await page.goto(PORTAL + t.hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(12000);

    // Open Actions > Add and remember which frame owns the dialog.
    let frame = null;
    for (const fr of page.frames()) {
      const b = await fr.evaluate(() => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        const x = window.Ext.ComponentQuery.query('button').filter((c) => !c.isDestroyed && vis(c) && (/actionsBtn$/i.test(c.itemId || '') || /^Actions$/i.test(c.text || ''))).pop();
        return x && x.getEl() ? x.getEl().dom.id : null;
      }).catch(() => null);
      if (!b) continue;
      await fr.locator('#' + b).click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(1500);
      const add = await fr.evaluate(() => {
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        const it = window.Ext.ComponentQuery.query('menu').filter(vis).flatMap((m) => m.query('menuitem'))
          .filter((i) => !i.disabled && /^\s*Add\s*$/i.test(String(i.text || '').replace(/<[^>]*>/g, '')))[0];
        return it && it.getEl() ? it.getEl().dom.id : null;
      }).catch(() => null);
      if (add) { await fr.locator('#' + add).click({ timeout: 5000 }).catch(() => {}); frame = fr; break; }
    }
    if (!frame) { console.log(`${t.label}: no enabled Add in Actions`); continue; }
    await page.waitForTimeout(5000);

    const steps = [];
    for (let s = 0; s < MAX_STEPS; s++) {
      const snap = await snapshot(frame).catch(() => null);
      if (!snap) break;
      steps.push(snap);
      console.log(`${t.label} step ${s + 1}: "${snap.title}" — ${snap.fields.length} fields [${snap.buttons.map((b) => b.text + (b.disabled ? '*' : '')).join(', ')}]`);
      for (const f of snap.fields) console.log(`    ${f.field} "${f.label}" ${f.type}${f.required ? ' REQUIRED' : ''}${f.options ? ` options=${JSON.stringify(f.options.slice(0, 6))}` : ''}`);

      const next = snap.buttons.find((b) => /^next$/i.test(b.text) && !b.disabled);
      if (!next) break;                       // Finish/Save is never clicked: this walk creates nothing.

      // Give every empty combo its first option, so Next has something valid to advance on.
      await frame.evaluate(() => {
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        const win = window.Ext.ComponentQuery.query('window').filter(vis).pop();
        for (const f of win.query('field').filter(vis)) {
          if (f.getValue && f.getValue()) continue;
          const st = f.getStore && f.getStore();
          if (st && st.getCount && st.getCount() > 0) f.setValue(st.getAt(0).get(f.valueField || 'code'));
        }
      }).catch(() => {});
      await page.waitForTimeout(1200);
      await frame.locator('#' + next.dom).click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(4000);
    }

    // Leave without saving.
    await frame.evaluate(() => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
      const win = window.Ext.ComponentQuery.query('window').filter(vis).pop();
      if (win) win.close();
    }).catch(() => {});

    out.wizards[t.label] = { hash: t.hash, entry: 'Actions menu > Add', steps };
  }
  out.generated_by = 'tools/cdp/walk-wizard.mjs';
  out.readOnly = 'walks forward and cancels; never clicks Finish/Save';
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
