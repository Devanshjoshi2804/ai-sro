/*
 * capture-screen-network.mjs — visit a screen and record every call it actually makes.
 *
 * Two dimensions are stuck for the same reason. 88 screens have NO known read resource at all, and
 * 69 more name resources whose response body was never recorded. Both were mapped by reading the
 * ExtJS store configuration, which misses anything a screen fetches at runtime — which is most of
 * the operational tier: shipping, receiving, picking, yard.
 *
 * So stop inferring and watch the wire. Navigate, listen, and record each `/data/WM` call the screen
 * issues, with its response. That closes read_apis (the screen's resources become observed rather
 * than declared) and read_shapes (a real body per resource) in one pass, and every entry is backed
 * by a stored exchange rather than a store config.
 *
 * Read-only: it navigates and listens. It clicks nothing.
 *
 *   node tools/cdp/capture-screen-network.mjs            every screen missing either dimension
 *   node tools/cdp/capture-screen-network.mjs 20         first 20 (smoke run)
 *   node tools/cdp/capture-screen-network.mjs shipping   one area
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const MAP = `${KG}/index/app-map.json`;
const OUT = `${KG}/index/screen-network.json`;
const HTTP_DIR = `${KG}/http`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));
const KEEP_ROWS = 2;

const mapFile = JSON.parse(fs.readFileSync(MAP, 'utf8'));
const coverage = JSON.parse(fs.readFileSync(`${KG}/index/coverage.json`, 'utf8'));
const needs = new Set(coverage.screens
  .filter((s) => s.dimensions.read_apis === false || s.dimensions.read_shapes === false)
  .map((s) => s.hash));

const fresh = process.argv.includes('--fresh');
const arg = process.argv.slice(2).find((a) => !a.startsWith('--'));
let targets = mapFile.screens.filter((s) => needs.has(s.hash));
/*
 * With --fresh, retry exactly the screens that showed nothing last time rather than the whole set:
 * a zero-call screen is the only case a reload can change.
 */
if (fresh && fs.existsSync(OUT)) {
  const prior = JSON.parse(fs.readFileSync(OUT, 'utf8')).screens || {};
  const silent = new Set(Object.entries(prior).filter(([, v]) => !v.calls?.length).map(([h]) => h));
  targets = mapFile.screens.filter((s) => silent.has(s.hash));
}
if (arg && !/^\d+$/.test(arg)) targets = targets.filter((s) => s.area === arg || s.tier === arg);
if (arg && /^\d+$/.test(arg)) targets = targets.slice(0, Number(arg));

/* Which resources already have a recorded GET body — so a screen's own reads are not re-stored. */
const haveBody = new Set();
for (const f of fs.readdirSync(path.join(HTTP_DIR, 'exchanges'))) {
  const rows = fs.readFileSync(path.join(HTTP_DIR, 'exchanges', f), 'utf8').split('\n').filter(Boolean);
  for (const l of rows) {
    // A stored 422 has a body too — an error body. Only a SUCCESSFUL read counts as having the shape;
    // treating any body as proof made the capture skip the real 200 on tableColumns and
    // shippingProgressEach, both of which the app fetches with parameters we had not guessed.
    try { const r = JSON.parse(l); if (r.request?.method === 'GET' && r.response?.body != null && r.response?.status < 300) { haveBody.add(f.replace('.jsonl', '')); break; } } catch {}
  }
}

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

let bucket = [];
page.on('requestfinished', async (req) => {
  if (!/\/data\/WM\//.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null;
  try { body = await res?.json(); } catch { body = null; }
  bucket.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, ''),
    status: res?.status(), headers: strip(res?.headers()), body,
  });
});

try {
  await page.goto(PORTAL + '#wm.config/wm.config.warehouse.warehouse////', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  let i = 0, newResources = 0, newBodies = 0;
  for (const t of targets) {
    i++;
    /*
     * `--fresh` reloads before every screen. 51 screens produced ZERO calls on the first pass, and a
     * screen that fetches nothing is indistinguishable from a screen whose store was already loaded
     * earlier in the same session — the SPA keeps them. A reload makes the difference observable.
     */
    if (fresh) {
      await page.evaluate(() => { window.location.reload(); }).catch(() => {});
      await page.waitForTimeout(9000);
    } else {
      await resetFramesIfNeeded(page);
    }
    bucket = [];
    await page.evaluate((h) => { window.location.hash = h; }, t.hash).catch(() => {});
    await page.waitForTimeout(t.tier === 'operational' ? 8000 : 5500);

    const calls = bucket.slice();
    const resources = [...new Set(calls
      .map((c) => (c.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1])
      .filter(Boolean))];

    /* Store one exchange per resource whose body has never been recorded. */
    for (const r of resources) {
      if (haveBody.has(r)) continue;
      const call = calls.find((c) => c.method === 'GET' && c.status === 200 && c.body != null
        && new RegExp(`/wm/${r}(/|\\?|$)`).test(c.url));
      if (!call) continue;
      const data = call.body?.data;
      const rec = {
        ts: new Date().toISOString(), tool: 'tools/cdp/capture-screen-network.mjs', case: 'read-shape-observed',
        request: { method: 'GET', url: call.url.replace('/data/WM', '').split('?')[0], query: Object.fromEntries(new URLSearchParams(call.url.split('?')[1] || '')), headers: { accept: 'application/json' } },
        response: { status: call.status, headers: call.headers, body: call.body, kind: 'OK' },
        notes: `Observed while loading the ${t.label} screen — this resource was never in any store config, so it could only be found by watching the wire.`,
      };
      // Same size rule as the rest of the store: keep the shape, not the table.
      if (Array.isArray(data) && data.length > KEEP_ROWS) {
        rec.response.body = { ...call.body, data: data.slice(0, KEEP_ROWS) };
        rec.response.body_truncated = { rows_returned: data.length, rows_kept: KEEP_ROWS, by: 'tools/cdp/capture-screen-network.mjs' };
      }
      fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${r}.jsonl`), JSON.stringify(rec) + '\n');
      haveBody.add(r);
      newBodies++;
    }

    /* Teach app-map what the screen really reads, with provenance. */
    const screen = mapFile.screens.find((s) => s.hash === t.hash);
    const before = new Set(screen.resources || []);
    screen.resources = [...new Set([...(screen.resources || []), ...resources])];
    screen.resources_observed_by = 'tools/cdp/capture-screen-network.mjs';
    newResources += screen.resources.length - before.size;

    store.screens[t.hash] = {
      label: t.label, area: t.area, tier: t.tier,
      calls: calls.map((c) => ({ method: c.method, url: c.url.split('?')[0], status: c.status })),
      resources,
      non_get: calls.filter((c) => c.method !== 'GET').map((c) => `${c.method} ${c.url.split('?')[0]} -> ${c.status}`),
    };
    process.stderr.write(`  [${i}/${targets.length}] ${t.label.padEnd(34)} ${calls.length} calls · ${resources.length} resources${resources.length ? ' · ' + resources.slice(0, 4).join(',') : ''}\n`);

    if (i % 15 === 0) {
      fs.writeFileSync(MAP, JSON.stringify(mapFile, null, 2) + '\n');
      fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/capture-screen-network.mjs', screens: store.screens }, null, 2) + '\n');
    }
  }

  fs.writeFileSync(MAP, JSON.stringify(mapFile, null, 2) + '\n');
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-screen-network.mjs',
    what_this_is: 'Every /data/WM call each screen issues on load, observed rather than inferred from store config. Screens whose resources were previously unknown get them from here.',
    totals: { screens: Object.keys(store.screens).length, resources_added_to_app_map: newResources, new_response_bodies: newBodies },
    screens: store.screens,
  }, null, 2) + '\n');
  console.log(JSON.stringify({ screens: targets.length, resources_added: newResources, new_bodies: newBodies }, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
