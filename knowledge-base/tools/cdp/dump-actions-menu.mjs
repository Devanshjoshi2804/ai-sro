/*
 * dump-actions-menu.mjs — enumerate the Actions menu on screens that have no Add button.
 *
 * WHY: `/wm/locations` holds 61,912 rows, but NONE of the ten location screens reports
 * can_create. They are overview dashboards whose toolbars carry an "Actions" split button and
 * drill-in buttons ("Dock Doors255", "Dock Sets7") instead. So the create path for the largest
 * table in the system is behind a menu the screen map never opened, and the map's `can_create:false`
 * means "no Add button", not "cannot create".
 *
 * Read-only: opens the menu, reads its items, closes it. Never activates an item.
 *
 *   node tools/cdp/dump-actions-menu.mjs "Storage Locations" "Dock Locations"
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const OUT = `${KG}/index/actions-menus.json`;

const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const wanted = process.argv.slice(2);
const targets = screens.filter((s) => wanted.includes(s.label));
if (!targets.length) { console.error('no matching screens'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const out = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { screens: {} };

try {
  for (const t of targets) {
    await page.goto(PORTAL + t.hash, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(12000);

    const rec = { hash: t.hash, toolbar: (t.actions || []).map((a) => a.label || a.itemId), menus: [] };

    // Any button whose itemId ends in actionsBtn owns the menu; there may be more than one frame.
    for (const fr of page.frames()) {
      const ids = await fr.evaluate(() => {
        if (!window.Ext) return [];
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        return window.Ext.ComponentQuery.query('button')
          .filter((b) => !b.isDestroyed && vis(b) && (/actionsBtn$/i.test(b.itemId || '') || /^Actions$/i.test(b.text || '')))
          .map((b) => ({ itemId: b.itemId, text: b.text, dom: b.getEl() && b.getEl().dom.id }));
      }).catch(() => []);
      for (const b of ids) {
        if (!b.dom) continue;
        await fr.locator('#' + b.dom).click({ timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(1500);
        // The menu renders into the frame's own floating layer, not the button's container.
        const items = await fr.evaluate(() => {
          if (!window.Ext) return [];
          const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
          return window.Ext.ComponentQuery.query('menu').filter(vis)
            .flatMap((m) => m.query('menuitem').map((i) => ({
              text: String(i.text || '').replace(/<[^>]*>/g, '').trim(),
              itemId: i.itemId, disabled: !!i.disabled, hasSubmenu: !!i.menu,
            })));
        }).catch(() => []);
        rec.menus.push({ button: b.text || b.itemId, item_count: items.length, items });
        await page.keyboard.press('Escape').catch(() => {});
        await page.waitForTimeout(600);
      }
    }
    out.screens[t.label] = rec;
    console.log(`${t.label}: ${rec.menus.reduce((a, m) => a + m.item_count, 0)} menu items across ${rec.menus.length} menus`);
    for (const m of rec.menus) for (const i of m.items) console.log(`   ${m.button} > ${i.text}${i.disabled ? ' (disabled)' : ''}${i.hasSubmenu ? ' >' : ''}`);
  }
  out.generated_by = 'tools/cdp/dump-actions-menu.mjs';
  out.readOnly = true;
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
