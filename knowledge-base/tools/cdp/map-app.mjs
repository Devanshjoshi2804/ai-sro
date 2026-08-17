/*
 * map-app.mjs — Phase 0: build the complete structural inventory of the application.
 *
 * GOAL
 * One record per screen describing everything an operator or an agent could do there, without
 * doing any of it. This is the map we work through afterwards, screen by screen.
 *
 * For each screen:
 *   - what data it shows      (grid columns, row counts)
 *   - what can be performed   (toolbar actions, recorded but never pressed)
 *   - what can be set         (form fields: JSON name, label, required, type, maxLength)
 *   - what it depends on      (the resources it reads on load)
 *   - what kind of screen it is (grid / form / dashboard / mixed)
 *
 * STRICTLY READ-ONLY. It navigates, waits, and reads component state. It never clicks Save,
 * never invokes a grid-action plugin, never submits. Many of these screens sit in front of live
 * inventory and open work, so discovery must not mutate anything.
 *
 * Scope comes from two harvested sources rather than by walking menus by hand:
 *   index/app-routes.json    207 routes incl. 173 Configuration screens, with nav_path labels
 *   tools/cdp/tier2-routes.json  123 operational sub-routes discovered from their nav bars
 *
 *   node tools/cdp/map-app.mjs config inventory    one Configuration area
 *   node tools/cdp/map-app.mjs config              all Configuration areas
 *   node tools/cdp/map-app.mjs ops                 all operational sub-routes
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';

const KG = 'knowlegde_graph/blue-yonder-sce';
const OUT = `${KG}/index/app-map.json`;

const routes = JSON.parse(fs.readFileSync(`${KG}/index/app-routes.json`, 'utf8'));
const tier2 = JSON.parse(fs.readFileSync('tools/cdp/tier2-routes.json', 'utf8'));

/* Build the work list: Configuration screens carry a nav_path; operational ones carry an area. */
function targets(mode, filter) {
  if (mode === 'ops') {
    return Object.entries(tier2).flatMap(([area, list]) => list
      .filter(() => !filter || area === filter)
      .map((r) => ({ app: area, area, label: r.text, hash: r.href, tier: 'operational' })));
  }
  return routes
    .filter((r) => /^#wm\.config\//.test(r.hash || ''))
    .map((r) => {
      const m = /#wm\.config\/wm[.-]config[.-]([a-z]+)/.exec(r.hash) || [];
      return { app: 'configuration', area: m[1] || 'other', label: r.label, hash: r.hash,
        nav_path: r.nav_path, tier: 'configuration' };
    })
    .filter((r) => !filter || r.area === filter);
}

/*
 * Read everything on screen through the ExtJS component tree.
 * Only components with a real bounding box count: this SPA never tears down visited screens, so
 * queries otherwise return dozens of cached off-screen grids and forms from earlier navigation.
 */
/*
 * Inspect ACROSS ALL FRAMES.
 *
 * The portal nests up to 6 iframes and not every screen renders in the first one: Allocation
 * Rules, for example, draws in a different frame entirely, so inspecting only
 * document.querySelector('iframe') reported it as an empty dashboard. Evaluate in every frame and
 * keep whichever actually has the ExtJS components.
 */
const inspectFrame = (frame) => frame.evaluate(() => {
  const w = window.Ext ? window : null;
  if (!w) return { error: 'Ext not available' };
  const vis = (c) => {
    const d = c.getEl && c.getEl() && c.getEl().dom;
    const r = d && d.getBoundingClientRect();
    return r && r.width > 0 && r.height > 0;
  };

  const grids = w.Ext.ComponentQuery.query('grid').filter(vis).map((g) => ({
    rows: g.getStore ? g.getStore().getCount() : null,
    total: g.getStore && g.getStore().getTotalCount ? g.getStore().getTotalCount() : null,
    // The first column's xtype tells us how a record is opened on this screen.
    open_mechanism: (g.columns || [])[0]?.xtype || null,
    columns: (g.columns || []).map((c) => ({
      label: c.text ? String(c.text).replace(/<[^>]*>/g, '').trim() : null,
      field: c.dataIndex || null, xtype: c.xtype,
    })).filter((c) => c.label || c.field),
  }));

  const forms = w.Ext.ComponentQuery.query('form').filter(vis).map((fm) => {
    const items = fm.getForm().getFields().items;
    return {
      field_count: items.length,
      fields: items.map((x) => ({
        field: x.name, label: x.fieldLabel, required: x.allowBlank === false,
        type: x.xtype, maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
        // A combo's options are part of "what can be set" on this screen.
        options: x.getStore && x.getStore() && x.getStore().getCount && x.getStore().getCount() > 0 && x.getStore().getCount() <= 12
          ? x.getStore().getRange().map((r) => r.get(x.valueField || 'code')).filter(Boolean).slice(0, 12)
          : undefined,
      })),
    };
  });

  // Actions are inventoried, never invoked.
  const actions = w.Ext.ComponentQuery.query('button').filter((b) => !b.isDestroyed && vis(b))
    .map((b) => ({
      label: String(b.text || '').replace(/<[^>]*>/g, '').trim().slice(0, 40),
      itemId: b.itemId || null, disabled: !!b.disabled,
    }))
    .filter((b) => b.label || b.itemId);

  return { title: (document.title || '').replace('Blue Yonder - ', '').slice(0, 60), grids, forms, actions };
}).catch(() => ({ error: 'frame eval failed' }));

/* Pick the frame with the richest ExtJS content; fall back to the top document's title. */
async function inspect(page) {
  let best = { error: 'Ext not available', grids: [], forms: [], actions: [] };
  let bestScore = -1;
  for (const fr of page.frames()) {
    const r = await inspectFrame(fr);
    if (r.error) continue;
    const score = (r.grids?.length || 0) * 10 + (r.forms?.length || 0) * 10 + (r.actions?.length || 0);
    if (score > bestScore) { bestScore = score; best = r; }
  }
  const topTitle = await page.title().catch(() => '');
  best.title = (topTitle || best.title || '').replace('Blue Yonder - ', '').slice(0, 60);
  best.frames_scanned = page.frames().length;
  return best;
}

/*
 * Fingerprint the RENDERED content: grid column dataIndexes plus form field names.
 *
 * Route and title are NOT load signals on this app. Its view layer can wedge, after which every
 * navigation updates the URL and document.title correctly while the DOM stays frozen on the
 * previous screen - eleven picking screens were once recorded with a form belonging to none of
 * them, and nothing looked wrong. Requiring the fingerprint to CHANGE between screens is the only
 * reliable detector; anything unconfirmed is recorded as unverified rather than trusted.
 */
const fingerprint = (state) => JSON.stringify([
  (state.grids || []).map((g) => (g.columns || []).map((c) => c.field).join(',')),
  (state.forms || []).map((f) => f.fields.map((x) => x.field).join(',')),
]);

let lastPrint = '';

/*
 * The SPA attaches one iframe per visited screen and never releases them - 333 live frames after
 * a full crawl, one visible. That is what degrades it, wedges the view layer, and crashed the
 * renderer. Reset periodically; a soft reload preserves the session.
 */
async function resetFramesIfNeeded(page, limit = 30) {
  if (page.frames().length < limit) return false;
  const before = page.frames().length;
  /*
   * Reset EARLY. Letting frames pile up to 333 crashed the renderer during the reload itself,
   * and the browser had to be restarted - which loses the session, because it is held in a
   * session cookie that does not survive a Chrome restart. Resetting at ~30 keeps each reload
   * cheap and the app healthy.
   */
  await page.evaluate(() => { window.location.reload(); }).catch(() => {});
  await page.waitForTimeout(9000);
  for (let i = 0; i < 20 && page.frames().length < 2; i++) await page.waitForTimeout(700);
  process.stderr.write(`  [reset] frames ${before} -> ${page.frames().length}\n`);
  return true;
}

async function mapScreen(page, t) {
  const rec = { ...t, reads: [] };
  const pending = new Map();
  let seq = 0;
  const onReq = (q) => {
    if (!/\/data\//.test(q.url()) || /webPerformanceEntries|persistence|sessionKeepAlive/.test(q.url())) return;
    pending.set(q, { seq: seq++, method: q.method(), url: q.url().split('?')[0] });
  };
  const onRes = async (s) => {
    const c = pending.get(s.request());
    if (!c) return;
    pending.delete(s.request());
    c.status = s.status();
    try { const j = JSON.parse(await s.text()); c.rows = Array.isArray(j?.data) ? j.data.length : null; } catch {}
    rec.reads.push(c);
  };
  page.on('request', onReq); page.on('response', onRes);
  try {
    await resetFramesIfNeeded(page);
    await dismissBlocking(page);
    await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
    await page.waitForTimeout(1200);
    await page.evaluate((h) => { window.location.hash = h; }, t.hash);
    /*
     * Operational screens are much heavier than config ones: they attach many nested frames and
     * fetch live transactional data. One earlier run inspected while only ONE frame existed and
     * recorded a real grid screen as an empty dashboard, so give them a longer settle and a
     * longer poll, and wait for the frame tree to actually appear.
     */
    const heavy = t.tier === 'operational';
    await page.waitForTimeout(heavy ? 6000 : 2500);
    for (let i = 0; i < 10 && page.frames().length < 2; i++) await page.waitForTimeout(500);
    let state = await inspect(page);
    const deadline = Date.now() + (heavy ? 26000 : 14000);
    while (Date.now() < deadline && fingerprint(state) === lastPrint) {
      await page.waitForTimeout(900);
      state = await inspect(page);
    }
    const changed = fingerprint(state) !== lastPrint;
    lastPrint = fingerprint(state);
    Object.assign(rec, state);
    rec.content_changed = changed;
    rec.unverified = !changed;
    const dead = /^404$/i.test((state.title || '').trim());
    rec.route_dead = dead;
    rec.kind = dead ? 'dead-route'
      : state.grids?.length && state.forms?.length ? 'mixed'
      : state.grids?.length ? 'grid'
      : state.forms?.length ? 'form'
      : 'dashboard';
    // A screen with no Add button cannot create; that is a fact worth recording up front.
    rec.can_create = (state.actions || []).some((a) => a.itemId === 'addButton');
    rec.can_delete = (state.actions || []).some((a) => a.itemId === 'deleteButton');
    rec.can_copy = (state.actions || []).some((a) => a.itemId === 'copyButton');
  } catch (e) {
    rec.error = String(e).split('\n')[0].slice(0, 160);
  } finally {
    page.off('request', onReq); page.off('response', onRes);
  }
  rec.reads.sort((a, b) => a.seq - b.seq);
  rec.resources = [...new Set(rec.reads.map((r) => (/\/data\/WM\/wm\/([A-Za-z][A-Za-z0-9_]*)/.exec(r.url) || [])[1]).filter(Boolean))];
  return rec;
}

const [mode, filter] = process.argv.slice(2);
const list = targets(mode || 'config', filter);
console.error(`mapping ${list.length} screens (mode=${mode || 'config'}${filter ? ', filter=' + filter : ''})`);

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];

const existing = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { screens: [] };
const byHash = new Map(existing.screens.map((s) => [s.hash, s]));

let done = 0;
for (const t of list) {
  const rec = await mapScreen(page, t);
  byHash.set(t.hash, rec);
  done++;
  process.stderr.write(`  [${done}/${list.length}] ${t.area}/${t.label}: ${rec.kind}`
    + ` grids=${rec.grids?.length ?? 0} formFields=${rec.forms?.[0]?.field_count ?? 0}`
    + ` create=${rec.can_create ? 'Y' : 'n'} res=${rec.resources?.length ?? 0}`
    + `${rec.unverified ? ' UNVERIFIED' : ''}${rec.error ? ' ERR' : ''}\n`);
  if (done % 10 === 0) {
    fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/map-app.mjs', readOnly: true, screens: [...byHash.values()] }, null, 2) + '\n');
  }
}
fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/map-app.mjs', readOnly: true, screens: [...byHash.values()] }, null, 2) + '\n');
const all = [...byHash.values()];
console.log(JSON.stringify({
  screensMapped: all.length,
  byKind: all.reduce((a, s) => (a[s.kind] = (a[s.kind] || 0) + 1, a), {}),
  creatable: all.filter((s) => s.can_create).length,
  errors: all.filter((s) => s.error).length,
}, null, 1));
await browser.close();
