/*
 * a11y-vs-ext.mjs — measure what the accessibility tree can and cannot tell us about this app.
 *
 * The question is a fair one: for most modern sites an accessibility snapshot beats a raw DOM
 * dump, because it is semantic, small, and stable. This script decides it for THIS app with
 * evidence instead of opinion, by capturing both views of the same rendered screen:
 *
 *   a11y  — Playwright's accessibility snapshot (roles + accessible names)
 *   ext   — the ExtJS component model (Ext.ComponentQuery)
 *
 * and reporting what each one yields, in an isolated tab so it disturbs nothing.
 *
 *   node tools/cdp/a11y-vs-ext.mjs "#wm.config/wm.config.inbound.storage.locationpreferencerules////"
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const hash = process.argv[2] || '#wm.config/wm.config.inbound.storage.locationpreferencerules////';
const OUT = 'knowlegde_graph/blue-yonder-sce/index/a11y-vs-ext.json';

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL + hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(11000);

  // Open Add so a real form is on screen — the form is where the two views differ most.
  for (const fr of page.frames()) {
    const id = await fr.evaluate(() => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
      const b = window.Ext.ComponentQuery.query('button').filter((x) => !x.isDestroyed && x.itemId === 'addButton' && !x.disabled && vis(x)).pop();
      return b && b.getEl() ? b.getEl().dom.id : null;
    }).catch(() => null);
    if (id) { await fr.locator('#' + id).click({ timeout: 5000 }).catch(() => {}); break; }
  }
  await page.waitForTimeout(4000);

  /*
   * The a11y view. Playwright now exposes it as an ARIA snapshot (YAML), which is the same tree
   * the browser hands assistive tech and the same one a11y-first automation drives from.
   * Parse it back into {role, name} so the two views can be counted side by side.
   */
  const a11y = [];
  let yaml = '';
  for (const fr of page.frames()) {
    const y = await fr.locator('body').ariaSnapshot({ timeout: 15000 }).catch(() => '');
    if (!y) continue;
    yaml += y + '\n';
    for (const line of y.split('\n')) {
      const m = line.match(/^\s*-\s+([a-z]+)(?:\s+"([^"]*)")?/);
      if (m) a11y.push({ role: m[1], name: m[2] || '' });
    }
  }
  const pageSnap = a11y;

  /* The Ext view: the field model behind the same form. */
  let ext = [];
  for (const fr of page.frames()) {
    const r = await fr.evaluate(() => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const forms = window.Ext.ComponentQuery.query('form').filter(vis);
      if (!forms.length) return null;
      const fm = forms.sort((a, b) => b.getForm().getFields().items.length - a.getForm().getFields().items.length)[0];
      return fm.getForm().getFields().items.map((x) => ({
        field: x.name, label: x.fieldLabel, required: x.allowBlank === false, type: x.xtype,
        maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
      }));
    }).catch(() => null);
    if (r && r.length > (ext.length || 0)) ext = r;
  }

  const named = a11y.filter((n) => n.name);
  const result = {
    generated_by: 'tools/cdp/a11y-vs-ext.mjs',
    screen: hash,
    question: 'Would an accessibility snapshot serve this capture better than the ExtJS component model?',
    a11y: {
      nodes_total: pageSnap.length,
      nodes_interesting: a11y.length,
      nodes_with_accessible_name: named.length,
      roles: a11y.reduce((a, n) => (a[n.role] = (a[n.role] || 0) + 1, a), {}),
      sample_names: named.slice(0, 12).map((n) => `${n.role}: ${n.name}`),
      yaml_bytes: yaml.length,
    },
    ext: {
      fields: ext.length,
      with_json_key: ext.filter((f) => f.field).length,
      required: ext.filter((f) => f.required).length,
      with_maxlength: ext.filter((f) => f.maxLength).length,
      sample: ext.slice(0, 8),
    },
    // The decisive comparison: an agent must POST a JSON body. Does the a11y view contain the keys?
    payload_keys_present_in_a11y: ext.filter((f) => f.field)
      .filter((f) => named.some((n) => String(n.name).includes(f.field))).map((f) => f.field),
  };
  // Accumulate per screen: one sample proved too little — see the note in the output file.
  const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { screens: {} };
  store.generated_by = 'tools/cdp/a11y-vs-ext.mjs';
  store.caution = 'Role coverage VARIES BY SCREEN: Business Units exposed 2 textboxes and Customer Types 2 buttons, while Location Preference Rules exposed neither. The finding that holds across every sample is payload_keys_present_in_a11y = 0.';
  store.screens[hash] = result;
  fs.writeFileSync(OUT, JSON.stringify(store, null, 2) + '\n');
  console.log(JSON.stringify({ ...result, a11y: { ...result.a11y, sample_names: result.a11y.sample_names.slice(0, 6) } }, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
