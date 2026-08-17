/*
 * capture-a11y.mjs — record the accessibility graph of every screen, next to its component model.
 *
 * The two views answer different questions and the base should hold both:
 *   ARIA snapshot  — roles and accessible names, the graph an a11y-first driver would steer by
 *   Ext model      — button itemIds and field JSON keys, what the application calls its own controls
 *
 * Measuring four screens showed role coverage is erratic rather than absent (index/a11y-vs-ext.json).
 * Erratic is the dangerous kind: a driver finds its control by role on one screen and silently finds
 * nothing on the next. Recording both per screen turns that into a lookup — for any screen, whether
 * a role-based strategy will work, and what to fall back to when it will not.
 *
 * Read-only: navigates and reads. Opens nothing, clicks nothing.
 *
 *   node tools/cdp/capture-a11y.mjs                 every screen
 *   node tools/cdp/capture-a11y.mjs configuration   one tier
 *   node tools/cdp/capture-a11y.mjs 20              first 20 (smoke run)
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const OUT = `${KG}/index/a11y-map.json`;
const TREES = `${KG}/index/a11y-trees.jsonl`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const arg = process.argv[2];
const targets = /^\d+$/.test(arg || '')
  ? screens.slice(0, Number(arg))
  : screens.filter((s) => !arg || s.tier === arg || s.area === arg);

/* The SPA never releases an iframe; 333 accumulated frames crashed the renderer once. Reset at 30. */
async function resetFramesIfNeeded(page, limit = 30) {
  if (page.frames().length < limit) return;
  const before = page.frames().length;
  await page.evaluate(() => { window.location.reload(); }).catch(() => {});
  await page.waitForTimeout(9000);
  process.stderr.write(`  [reset] frames ${before} -> ${page.frames().length}\n`);
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { screens: {} };

try {
  await page.goto(PORTAL + '#wm.config/wm.config.warehouse.warehouse////', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  let i = 0;
  for (const t of targets) {
    i++;
    const rec = { hash: t.hash, label: t.label, area: t.area, tier: t.tier };
    try {
      await resetFramesIfNeeded(page);
      await page.evaluate((h) => { window.location.hash = h; }, t.hash);
      await page.waitForTimeout(t.tier === 'operational' ? 6000 : 4000);

      /* ARIA side: parse the YAML back into role/name pairs so the two views can be counted. */
      const nodes = [];
      let yaml = '';
      for (const fr of page.frames()) {
        const y = await fr.locator('body').ariaSnapshot({ timeout: 8000 }).catch(() => '');
        if (!y) continue;
        yaml += y + '\n';
        for (const line of y.split('\n')) {
          const m = line.match(/^\s*-\s+([a-z]+)(?:\s+"([^"]*)")?/);
          if (m) nodes.push({ role: m[1], name: m[2] || '' });
        }
      }

      /* Ext side: the controls the app itself would address. */
      let ext = { buttons: [], fields: [] };
      for (const fr of page.frames()) {
        const r = await fr.evaluate(() => {
          if (!window.Ext) return null;
          const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
          return {
            buttons: window.Ext.ComponentQuery.query('button').filter((b) => !b.isDestroyed && vis(b))
              .map((b) => ({ itemId: b.itemId, text: String(b.text || '').replace(/<[^>]*>/g, '').trim(), disabled: !!b.disabled })),
            fields: window.Ext.ComponentQuery.query('field').filter(vis)
              .map((f) => ({ field: f.name, label: String(f.fieldLabel || '').replace(/<[^>]*>/g, '').trim(), type: f.xtype })),
          };
        }).catch(() => null);
        if (r && (r.buttons.length + r.fields.length) > (ext.buttons.length + ext.fields.length)) ext = r;
      }

      const roles = nodes.reduce((a, n) => (a[n.role] = (a[n.role] || 0) + 1, a), {});
      // Can a role-driven click reach this screen's buttons at all?
      const namedButtons = nodes.filter((n) => n.role === 'button' && n.name).map((n) => n.name);
      const extButtonTexts = ext.buttons.filter((b) => b.text).map((b) => b.text);
      rec.a11y = {
        nodes: nodes.length,
        roles,
        named: nodes.filter((n) => n.name).length,
        yaml_bytes: yaml.length,
      };
      rec.ext = { buttons: ext.buttons.length, fields: ext.fields.length };
      rec.role_strategy = {
        ext_buttons_visible: extButtonTexts.length,
        reachable_by_role_and_name: extButtonTexts.filter((x) => namedButtons.includes(x)).length,
        unreachable: extButtonTexts.filter((x) => !namedButtons.includes(x)).slice(0, 12),
      };
      rec.payload_keys_in_tree = ext.fields.filter((f) => f.field)
        .filter((f) => nodes.some((n) => n.name.includes(f.field))).length;

      fs.appendFileSync(TREES, JSON.stringify({ hash: t.hash, label: t.label, yaml }) + '\n');
    } catch (e) {
      rec.error = String(e).split('\n')[0].slice(0, 140);
    }
    store.screens[t.hash] = rec;
    process.stderr.write(`  [${i}/${targets.length}] ${t.label.padEnd(34)} `
      + (rec.error ? 'ERR ' + rec.error : `a11y ${String(rec.a11y.nodes).padStart(4)} nodes · ext ${rec.ext.buttons}b/${rec.ext.fields}f · role-reachable ${rec.role_strategy.reachable_by_role_and_name}/${rec.role_strategy.ext_buttons_visible}`) + '\n');
    if (i % 15 === 0) fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/capture-a11y.mjs', screens: store.screens }, null, 2) + '\n');
  }

  const all = Object.values(store.screens).filter((s) => !s.error && s.role_strategy);
  const btnTotal = all.reduce((a, s) => a + s.role_strategy.ext_buttons_visible, 0);
  const btnReach = all.reduce((a, s) => a + s.role_strategy.reachable_by_role_and_name, 0);
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-a11y.mjs',
    what_this_is: 'Per screen: the ARIA role/name graph, the ExtJS control model, and how much of the latter a role-and-name strategy can actually reach. Full ARIA YAML per screen is in a11y-trees.jsonl.',
    totals: {
      screens: all.length,
      ext_buttons_visible: btnTotal,
      reachable_by_role_and_name: btnReach,
      reach_rate: btnTotal ? `${Math.round(btnReach / btnTotal * 100)}%` : 'n/a',
      screens_with_zero_button_role: all.filter((s) => !(s.a11y.roles.button > 0)).length,
      payload_keys_in_tree: all.reduce((a, s) => a + (s.payload_keys_in_tree || 0), 0),
    },
    screens: store.screens,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ screens: all.length, reach_rate: btnTotal ? Math.round(btnReach / btnTotal * 100) + '%' : 'n/a' }, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
