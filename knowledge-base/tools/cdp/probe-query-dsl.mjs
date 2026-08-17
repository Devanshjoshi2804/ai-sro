/*
 * probe-query-dsl.mjs — learn how to ASK this API a question.
 *
 * The largest hole in this base is not an endpoint, it is a verb. Of 298 recorded calls carrying a
 * `query=` parameter, 295 sent `query=[]` — "give me the first N rows". Nothing here knows how to
 * say "the LPN with this id", "orders for this customer", "counts since Tuesday". An agent that can
 * only page blindly cannot verify a post-condition on a 61,912-row table.
 *
 * Two sources are probed together:
 *   /rpux/filter/columns/<Entity>   158 endpoints describing what each grid can filter on — the
 *                                   schema of the query language, never called until now
 *   query=<json> against a resource  the grammar itself, established by trying forms and recording
 *                                   which the server accepts and what it returns
 *
 * Read-only throughout: every probe is a GET.
 *
 *   node tools/cdp/probe-query-dsl.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/query-dsl.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';

const get = (page, url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  return { status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 300) };
}, { url, base: BASE });

const record = (resource, rec) => fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify(rec) + '\n');

/*
 * The grammar candidates. ExtJS grids serialise filters as an array of objects, and this portal is
 * ExtJS — but which key names the server accepts is exactly the sort of thing that cannot be
 * guessed from the framework, so every plausible spelling is tried and the answer recorded.
 */
const FORMS = (field, value) => [
  ['ext-filter-property', JSON.stringify([{ property: field, value }])],
  ['ext-filter-operator-eq', JSON.stringify([{ property: field, value, operator: '=' }])],
  ['ext-filter-field-key', JSON.stringify([{ field, value }])],
  ['ext-filter-like', JSON.stringify([{ property: field, value, operator: 'like' }])],
  ['name-value-pair', JSON.stringify([{ name: field, value }])],
  /*
   * The vocabulary the app's OWN filter metadata uses. /rpux/filter/columns/<Entity> describes each
   * filterable column as {columnName, dataType, filterType, funcGroup}, so the query is far more
   * likely to speak that language than ExtJS's generic `property`.
   */
  ['metadata-columnName-EQ', JSON.stringify([{ columnName: field, operator: 'EQ', value }])],
  ['metadata-columnName-eq-lower', JSON.stringify([{ columnName: field, operator: 'eq', value }])],
  ['metadata-columnName-value', JSON.stringify([{ columnName: field, value }])],
  ['metadata-with-datatype', JSON.stringify([{ columnName: field, dataType: 'S', operator: 'EQ', value }])],
  ['sql-like-string', `${field} = '${value}'`],
];

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const out = { generated_by: 'tools/cdp/probe-query-dsl.mjs', filter_metadata: {}, grammar: {}, notes: [] };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  /* 1. What does the app itself say each grid can be filtered on? */
  for (const entity of ['WMCarriers', 'WMAreas', 'WMLocations', 'WMItems']) {
    const r = await get(page, `/rpux/filter/columns/${entity}`);
    const cols = Array.isArray(r.body?.data) ? r.body.data : Array.isArray(r.body) ? r.body : [];
    out.filter_metadata[entity] = {
      status: r.status,
      column_count: cols.length,
      sample: cols.slice(0, 6),
    };
    record('rpux-filter', {
      ts: new Date().toISOString(), tool: 'tools/cdp/probe-query-dsl.mjs', case: 'filter-columns',
      request: { method: 'GET', url: `/rpux/filter/columns/${entity}`, headers: { accept: 'application/json' } },
      response: { status: r.status, body: cols.length > 6 ? { truncated_to: 6, data: cols.slice(0, 6), column_count: cols.length } : r.body, bodyRaw: r.bodyRaw },
      notes: 'The filterable columns the UI offers for this entity — the schema of the query language.',
    });
    console.log(`filter columns ${entity.padEnd(14)} -> ${r.status} ${cols.length} columns`);
  }

  /* 2. Establish the grammar against a resource whose contents are known. */
  const target = process.argv[2] || 'carriers';
  const baseline = await get(page, `/wm/${target}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`);
  const sample = baseline.body?.data?.[0];
  const field = sample ? Object.keys(sample).find((k) => typeof sample[k] === 'string' && k !== 'resourceId' && !k.endsWith('_uri')) : null;
  const value = sample?.[field];
  const totalRes = await get(page, `/wm/${target}/count?siteId=SG&subsites=----`);
  const total = totalRes.body?.data?.count ?? totalRes.body?.data ?? null;
  console.log(`\nbaseline: ${target} total=${JSON.stringify(total)}; filtering on ${field}=${JSON.stringify(value)}`);

  for (const [name, q] of FORMS(field, value)) {
    const url = `/wm/${target}?query=${encodeURIComponent(q)}&offset=0&limit=25&siteId=SG&subsites=----`;
    const r = await get(page, url);
    const rows = Array.isArray(r.body?.data) ? r.body.data : [];
    const matched = rows.length > 0 && rows.every((x) => x[field] === value);
    out.grammar[name] = {
      query: q, status: r.status, rows: rows.length,
      every_row_matches: matched,
      // A filter that changes nothing is a filter the server ignored, which is the dangerous case:
      // it looks like success and returns the wrong set.
      verdict: r.status !== 200 ? 'rejected' : matched ? 'APPLIED' : 'ignored (returned unfiltered rows)',
      error: (r.body?.errors || []).map((e) => e.userMessage).join('; ') || undefined,
    };
    record(target, {
      ts: new Date().toISOString(), tool: 'tools/cdp/probe-query-dsl.mjs', case: `query-form-${name}`,
      request: { method: 'GET', url: `/wm/${target}`, query: { query: q, limit: '25' }, headers: { accept: 'application/json' } },
      response: { status: r.status, body: rows.length > 2 ? { rows_returned: rows.length, data: rows.slice(0, 2) } : r.body, bodyRaw: r.bodyRaw },
      notes: `Testing whether the server honours this filter spelling. Baseline collection holds ${total} rows.`,
    });
    console.log(`  ${name.padEnd(24)} -> ${r.status} ${String(rows.length).padStart(4)} rows  ${out.grammar[name].verdict}`);
  }

  fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + '\n');
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
