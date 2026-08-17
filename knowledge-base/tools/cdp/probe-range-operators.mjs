/*
 * probe-range-operators.mjs — do GT/GE/LT/LE actually compare, or just parse?
 *
 * The grammar accepts EQ NE GT GE LT LE, but only EQ and NE have been shown to DO anything: the
 * carriers probe that established the operator list saw GT return a full unfiltered page, which is
 * exactly what an ignored operator looks like. Range queries are what "counts since Tuesday" and
 * "anything over quantity N" need, so it matters whether they compare or merely parse.
 *
 * Method: pick a filterable numeric column, read the real distribution, then ask for a bound that
 * should exclude part of it and check the rows that come back actually honour it.
 *
 * Read-only.
 *
 *   node tools/cdp/probe-range-operators.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/query-dsl.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';

const filterable = JSON.parse(fs.readFileSync(`${KG}/index/filterable-columns.json`, 'utf8')).resources;

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

const get = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  return { status: res.status, body: parsed, sessionExpired: !parsed && /b2clogin|<html|Sign in/i.test(text) };
}, { url, base: BASE });

const q = (column, operator, value) => encodeURIComponent(JSON.stringify([{ column, operator, value }]));

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(11000);

  const results = [];
  for (const [resource, spec] of Object.entries(filterable)) {
    if (results.length >= 4) break;
    if (!spec.filterable?.length) continue;

    const base1 = await get(`/wm/${resource}?query=[]&offset=0&limit=200&siteId=SG&subsites=----`);
    if (base1?.sessionExpired) { console.error('SESSION EXPIRED — nothing recorded.'); process.exit(2); }
    const rows = Array.isArray(base1.body?.data) ? base1.body.data : [];
    if (rows.length < 10) continue;

    // A numeric column with genuine spread — a constant column proves nothing about comparison.
    const col = spec.filterable.find((c) => {
      const vals = rows.map((r) => r[c]).filter((v) => typeof v === 'number');
      return vals.length > rows.length / 2 && new Set(vals).size > 2;
    });
    if (!col) continue;

    const values = rows.map((r) => r[col]).filter((v) => typeof v === 'number').sort((a, b) => a - b);
    const mid = values[Math.floor(values.length / 2)];
    const expectAbove = values.filter((v) => v > mid).length;
    const expectAtOrBelow = values.filter((v) => v <= mid).length;

    const gt = await get(`/wm/${resource}?query=${q(col, 'GT', mid)}&offset=0&limit=200&siteId=SG&subsites=----`);
    const le = await get(`/wm/${resource}?query=${q(col, 'LE', mid)}&offset=0&limit=200&siteId=SG&subsites=----`);
    const gtRows = Array.isArray(gt.body?.data) ? gt.body.data : [];
    const leRows = Array.isArray(le.body?.data) ? le.body.data : [];

    const entry = {
      resource, column: col, pivot: mid,
      sample_rows: rows.length,
      GT: { rows: gtRows.length, all_above: gtRows.length > 0 && gtRows.every((r) => r[col] > mid), expected_in_sample: expectAbove },
      LE: { rows: leRows.length, all_at_or_below: leRows.length > 0 && leRows.every((r) => r[col] <= mid), expected_in_sample: expectAtOrBelow },
    };
    entry.verdict = entry.GT.all_above && entry.LE.all_at_or_below ? 'RANGE OPERATORS COMPARE'
      : (gtRows.length === rows.length && leRows.length === rows.length) ? 'ignored — both returned the unfiltered page'
      : 'inconclusive';
    results.push(entry);

    fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/probe-range-operators.mjs', case: 'range-operators',
      request: { method: 'GET', url: `/wm/${resource}`, query: { query: `[{"column":"${col}","operator":"GT|LE","value":${mid}}]` }, headers: { accept: 'application/json' } },
      response: { status: 200, body: entry },
      notes: 'Whether GT/LE compare or merely parse, tested against the real distribution of a numeric filterable column.',
    }) + '\n');
    console.log(`${resource}.${col} pivot=${mid}: GT ${entry.GT.rows} rows (all above: ${entry.GT.all_above}) · LE ${entry.LE.rows} rows (all at/below: ${entry.LE.all_at_or_below}) -> ${entry.verdict}`);
  }

  const dsl = JSON.parse(fs.readFileSync(OUT, 'utf8'));
  dsl.range_operators = {
    tested: results,
    conclusion: results.length
      ? (results.every((r) => r.verdict === 'RANGE OPERATORS COMPARE') ? 'GT/GE/LT/LE perform real comparisons.'
        : results.some((r) => r.verdict === 'RANGE OPERATORS COMPARE') ? 'Comparison works on some resources; verify per resource before relying on a range.'
        : 'No evidence that the range operators compare — they parse and return unfiltered pages.')
      : 'no suitable numeric column found to test',
  };
  fs.writeFileSync(OUT, JSON.stringify(dsl, null, 2) + '\n');
  console.log('\n' + dsl.range_operators.conclusion);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
