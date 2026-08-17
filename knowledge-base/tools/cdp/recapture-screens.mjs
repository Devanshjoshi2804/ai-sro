/*
 * recapture-screens.mjs — re-read the structure of named screens that came back empty.
 *
 * Six screens have no grid columns, no form and no toolbar actions recorded. That is almost always
 * a capture artifact rather than an empty screen: the original crawl inspected them while the SPA
 * was still drawing, or while the view layer was wedged on the previous route. Revisiting one at a
 * time, with a reload before each, settles it — and where a screen really is empty, recording that
 * with a fresh look is worth more than leaving a hole.
 *
 * Read-only: navigates and reads the component tree.
 *
 *   node tools/cdp/recapture-screens.mjs "Permanent LPNs" "Movement Rules"
 *   node tools/cdp/recapture-screens.mjs --empty        every screen with no structure recorded
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const MAP = `${KG}/index/app-map.json`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

const mapFile = JSON.parse(fs.readFileSync(MAP, 'utf8'));
const args = process.argv.slice(2);
const wantEmpty = args.includes('--empty');
const names = args.filter((a) => !a.startsWith('--'));
const isEmpty = (s) => !(s.grids || []).some((g) => (g.columns || []).length) && !(s.forms || []).length && !(s.actions || []).length;
const targets = wantEmpty ? mapFile.screens.filter(isEmpty) : mapFile.screens.filter((s) => names.includes(s.label));
if (!targets.length) { console.error('no matching screens'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

try {
  await page.goto(PORTAL + '#wm.config/wm.config.warehouse.warehouse////', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  for (const t of targets) {
    // A reload before each: a wedged view layer keeps the previous screen's DOM under the new route.
    await page.evaluate(() => { window.location.reload(); }).catch(() => {});
    await page.waitForTimeout(9000);
    await page.evaluate((h) => { window.location.hash = h; }, t.hash).catch(() => {});
    await page.waitForTimeout(t.tier === 'operational' ? 9000 : 6500);

    let best = null;
    for (const fr of page.frames()) {
      const r = await fr.evaluate(() => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        return {
          url: location.href,
          grids: window.Ext.ComponentQuery.query('grid').filter(vis).map((g) => ({
            columns: (g.columns || []).map((c) => c.dataIndex).filter(Boolean),
            rows: g.getStore && g.getStore() ? g.getStore().getCount() : null,
          })),
          forms: window.Ext.ComponentQuery.query('form').filter(vis).map((f) => ({
            fields: f.getForm().getFields().items.map((x) => ({ field: x.name, label: clean(x.fieldLabel), type: x.xtype })),
          })),
          actions: window.Ext.ComponentQuery.query('button').filter(vis)
            .map((b) => ({ label: clean(b.text), itemId: b.itemId, disabled: !!b.disabled }))
            .filter((b) => b.itemId && !/^(user-button|siteButton)$/.test(b.itemId)),
        };
      }).catch(() => null);
      if (!r) continue;
      const weight = r.grids.reduce((a, g) => a + g.columns.length, 0) + r.forms.reduce((a, f) => a + f.fields.length, 0) + r.actions.length;
      if (!best || weight > best.weight) best = { ...r, weight };
    }

    const screen = mapFile.screens.find((s) => s.hash === t.hash);
    if (best && best.weight > 0) {
      screen.grids = best.grids;
      screen.forms = best.forms;
      screen.actions = best.actions;
      screen.structure_recaptured_by = 'tools/cdp/recapture-screens.mjs';
      console.log(`  ${t.label.padEnd(34)} grids ${best.grids.length} (${best.grids.reduce((a, g) => a + g.columns.length, 0)} cols) · forms ${best.forms.length} · actions ${best.actions.length}`);
    } else {
      screen.structure_recaptured_by = 'tools/cdp/recapture-screens.mjs';
      screen.structure_empty_confirmed = true;
      console.log(`  ${t.label.padEnd(34)} still empty after a reload — recorded as genuinely empty`);
    }
  }
  fs.writeFileSync(MAP, JSON.stringify(mapFile, null, 2) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
