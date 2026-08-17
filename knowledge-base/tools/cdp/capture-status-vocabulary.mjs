/*
 * capture-status-vocabulary.mjs — learn the state vocabulary of the operational tier.
 *
 * This base knows every endpoint and, since today, how to filter one. What it still cannot answer is
 * the question every verification asks: *what state is this thing in, and what states can it be in?*
 * An order, a wave, a shipment and an LPN all carry status fields whose legal values appear nowhere
 * in the help corpus as a list.
 *
 * They can be read out of the data. For every resource whose recorded shape has a status-like field,
 * page some rows and tally the distinct values, then confirm each value round-trips through the
 * filter grammar — which doubles as proof that the grammar works beyond the one resource it was
 * established on.
 *
 * Read-only: GETs only, nothing is written.
 *
 *   node tools/cdp/capture-status-vocabulary.mjs --dry
 *   node tools/cdp/capture-status-vocabulary.mjs 12
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/status-vocabulary.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const PAGE = 200;

const shapes = JSON.parse(fs.readFileSync(`${KG}/index/read-shapes.json`, 'utf8')).resources;

/*
 * A status field, without matching every code column in the system. `*Status` and `*State` are the
 * real targets; `statusDescription` is its label and is captured alongside rather than counted.
 */
const isStatus = (f) => /(^|[a-z])(status|state)$/i.test(f) && !/description|desc$/i.test(f);

const candidates = Object.entries(shapes)
  .filter(([, s]) => s.status === 200 && s.honours_limit !== false && (s.fields || []).some((f) => isStatus(f.field)))
  .map(([name, s]) => ({ resource: name, fields: s.fields.filter((f) => isStatus(f.field)).map((f) => f.field), rows: s.rows_returned }));

const arg = process.argv.find((a) => /^\d+$/.test(a));
const targets = arg ? candidates.slice(0, Number(arg)) : candidates;
console.log(`${candidates.length} resources carry a status-like field`);
if (process.argv.includes('--dry')) {
  for (const c of candidates) console.log(`  ${c.resource.padEnd(30)} ${c.fields.join(', ')}`);
  process.exit(0);
}

const getOnce = (page, url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  /*
   * An expired session does not fail — it 200s with the login page. A whole run once recorded
   * "0 rows" for 14 resources in a row, which reads as a fact about the app and is a fact about the
   * cookie. Detect it here and let the caller stop rather than write that down.
   */
  const login = !parsed && /b2clogin|<html|Sign in/i.test(text);
  return { status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 200), sessionExpired: login };
}, { url, base: BASE });

/* One retry: a navigation mid-probe is a transient, not a fact about the endpoint. */
async function get(page, url) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try { return await getOnce(page, url); }
    catch (e) {
      if (attempt) return { networkError: String(e).split('\n')[0].slice(0, 120) };
      await page.waitForTimeout(4000);
    }
  }
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const out = { generated_by: 'tools/cdp/capture-status-vocabulary.mjs', resources: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);
  /*
   * The portal keeps navigating itself for a while after load — the SPA settles its own route — and
   * a fetch issued into a context that is being torn down throws "Execution context was destroyed".
   * Wait for the URL to hold still before probing anything.
   */
  let last = '';
  for (let k = 0; k < 12; k++) {
    const now = page.url();
    if (now === last) break;
    last = now;
    await page.waitForTimeout(2500);
  }

  let i = 0;
  for (const t of targets) {
    i++;
    const r = await get(page, `/wm/${t.resource}?query=[]&offset=0&limit=${PAGE}&siteId=SG&subsites=----`);
    if (r?.sessionExpired) {
      console.error('\nSESSION EXPIRED — the API is answering with the login page. Nothing recorded.');
      console.error('Log in again in the attached Chrome, then re-run. No partial file is written.');
      process.exit(2);
    }
    const rows = Array.isArray(r.body?.data) ? r.body.data : [];
    const entry = { sampled_rows: rows.length, fields: {} };

    for (const field of t.fields) {
      const tally = {};
      for (const row of rows) {
        const v = row[field];
        if (v === null || v === undefined || v === '') continue;
        tally[String(v)] = (tally[String(v)] || 0) + 1;
      }
      const values = Object.entries(tally).sort((a, b) => b[1] - a[1]);
      // Pair each status with the description column beside it, where the resource carries one.
      const descField = Object.keys(rows[0] || {}).find((k) => k.toLowerCase() === `${field}description`.toLowerCase());
      const labels = {};
      if (descField) for (const row of rows) if (row[field] != null) labels[String(row[field])] = row[descField];

      /*
       * Only verify through the filter when the column is one this resource actually honours.
       * Roughly 60% of columns return 200-and-zero-rows for a value taken from their own row
       * (index/filterable-columns.json), so a failed filter there says nothing about the vocabulary.
       */
      const filterable = JSON.parse(fs.existsSync(`${KG}/index/filterable-columns.json`)
        ? fs.readFileSync(`${KG}/index/filterable-columns.json`, 'utf8') : '{"resources":{}}')
        .resources?.[t.resource]?.filterable;
      let verified = null;
      if (values.length && (!filterable || filterable.includes(field))) {
        const [val, count] = values[0];
        const q = encodeURIComponent(JSON.stringify([{ column: field, operator: 'EQ', value: val }]));
        const f = await get(page, `/wm/${t.resource}?query=${q}&offset=0&limit=${PAGE}&siteId=SG&subsites=----`);
        const frows = Array.isArray(f.body?.data) ? f.body.data : [];
        verified = {
          value: val, filtered_status: f.status, rows_returned: frows.length,
          every_row_matches: frows.length > 0 && frows.every((x) => String(x[field]) === val),
          count_in_sample: count,
        };
        fs.appendFileSync(path.join(EX, `${t.resource}.jsonl`), JSON.stringify({
          ts: new Date().toISOString(), tool: 'tools/cdp/capture-status-vocabulary.mjs', case: `filter-by-${field}`,
          request: { method: 'GET', url: `/wm/${t.resource}`, query: { query: JSON.stringify([{ column: field, operator: 'EQ', value: val }]), limit: String(PAGE) }, headers: { accept: 'application/json' } },
          response: { status: f.status, body: frows.length > 2 ? { rows_returned: frows.length, data: frows.slice(0, 2) } : f.body },
          notes: `Filtering ${t.resource} by its ${field}. Also a generalisation test for the query grammar, which was established on carriers.`,
        }) + '\n');
      }

      if (filterable && !filterable.includes(field)) verified = { skipped: 'this column is not filterable on this resource' };
      entry.fields[field] = { distinct_values: values.map(([v, n]) => ({ value: v, rows_in_sample: n, label: labels[v] ?? undefined })), verified_by_filter: verified };
    }

    out.resources[t.resource] = entry;
    const summary = Object.entries(entry.fields).map(([f, v]) => `${f}=${v.distinct_values.length} values${v.verified_by_filter?.every_row_matches ? ' (filter OK)' : ''}`).join(', ');
    console.log(`  [${i}/${targets.length}] ${t.resource.padEnd(28)} ${rows.length} rows · ${summary || 'no values in sample'}`);
    if (i % 10 === 0) fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
  }

  const all = Object.values(out.resources);
  out.totals = {
    resources: all.length,
    distinct_status_values: all.reduce((a, r) => a + Object.values(r.fields).reduce((b, f) => b + f.distinct_values.length, 0), 0),
    filters_verified: all.reduce((a, r) => a + Object.values(r.fields).filter((f) => f.verified_by_filter?.every_row_matches).length, 0),
  };
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
  console.log(JSON.stringify(out.totals, null, 1));
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
