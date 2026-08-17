/*
 * dump-toolbar-actions.mjs — the other 83 operational screens.
 *
 * The Actions-menu sweep covered 40 of 123 operational screens and produced 95 named verbs. The
 * remaining 83 expose their work some other way, and "some other way" was left as a gap. It is
 * almost always the toolbar: a row of buttons whose `itemId` is the app's own name for the action
 * (`facility-locations-dockdoor-actionsBtn`, `pckMthd_topOffPickBtn`).
 *
 * This reads them. Every visible button on the screen with its itemId, text and enabled state — no
 * clicks, no menus opened, nothing activated. It finishes the verb inventory for the tier.
 *
 *   node tools/cdp/dump-toolbar-actions.mjs --no-menu     screens with no Actions menu
 *   node tools/cdp/dump-toolbar-actions.mjs "Work Queue"
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const OUT = `${KG}/index/toolbar-actions.json`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const menus = fs.existsSync(`${KG}/index/actions-menus.json`)
  ? JSON.parse(fs.readFileSync(`${KG}/index/actions-menus.json`, 'utf8')).screens : {};

/* Chrome, site and navigation buttons are not screen actions. */
const CHROME = /^(user-button|siteButton|wm-cardDeck-back-button|first|prev|next|last)$/i;
const NAV_TEXT = /^(Configuration|Warehouse|Partners|Equipment|Work|Inventory|Inbound|Outbound|Production|Integration|Advanced|Workstation|Receiving|Shipping|Picking|Yard|Packing)$/i;

const args = process.argv.slice(2);
const noMenu = args.includes('--no-menu');
const named = args.filter((a) => !a.startsWith('--'));
const targets = noMenu
  ? screens.filter((s) => s.tier === 'operational' && !menus[s.label])
  : screens.filter((s) => named.includes(s.label));
if (!targets.length) { console.error('no matching screens'); process.exit(1); }
console.log(`${targets.length} screen(s) to read`);

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { screens: {} };

try {
  await page.goto(PORTAL + '#wm.config/wm.config.warehouse.warehouse////', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(10000);

  let i = 0;
  for (const t of targets) {
    i++;
    /*
     * Load each screen from scratch. Assigning location.hash after a reload left the portal on the
     * route it had just restored, and the screen's own frame never attached — every screen then read
     * as having no buttons. A full goto is what the working captures in this repo all use.
     */
    await page.goto(PORTAL + t.hash, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(13000);

    let best = [];
    for (const fr of page.frames()) {
      const b = await fr.evaluate(() => {
        if (!window.Ext) return [];
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        return window.Ext.ComponentQuery.query('button').filter(vis).map((x) => ({
          itemId: x.itemId || null,
          text: String(x.text || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim(),
          enabled: !x.disabled,
          menu: !!x.menu,
        }));
      }).catch(() => []);
      /*
       * Score frames by SCREEN buttons, not raw count. The portal chrome frame carries more buttons
       * than most screens — the whole top navigation — and picking by length chose it every time,
       * which is how a first pass reported "0 buttons" for 83 screens in a row.
       */
      const own = (list) => list.filter((x) => x.itemId && !CHROME.test(x.itemId) && !NAV_TEXT.test(x.text));
      if (own(b).length > own(best).length) best = b;
    }

    const actions = best.filter((b) => b.itemId && !CHROME.test(b.itemId) && !NAV_TEXT.test(b.text));
    store.screens[t.label] = { area: t.area, route: t.hash, buttons: actions };
    const enabled = actions.filter((a) => a.enabled);
    console.log(`  [${i}/${targets.length}] ${t.label.padEnd(34)} ${actions.length} button(s), ${enabled.length} enabled${enabled.length ? ': ' + enabled.slice(0, 5).map((a) => a.text || a.itemId).join(', ') : ''}`);
    if (i % 10 === 0) fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/dump-toolbar-actions.mjs', readOnly: 'buttons were read, never clicked', screens: store.screens }, null, 2) + '\n');
  }

  const all = Object.values(store.screens);
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/dump-toolbar-actions.mjs',
    readOnly: 'buttons were read, never clicked',
    totals: {
      screens: all.length,
      buttons: all.reduce((a, s) => a + s.buttons.length, 0),
      enabled: all.reduce((a, s) => a + s.buttons.filter((b) => b.enabled).length, 0),
      with_a_submenu: all.reduce((a, s) => a + s.buttons.filter((b) => b.menu).length, 0),
    },
    screens: store.screens,
  }, null, 2) + '\n');
  console.log(JSON.stringify(JSON.parse(fs.readFileSync(OUT, 'utf8')).totals, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
