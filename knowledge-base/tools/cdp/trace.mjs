/*
 * trace.mjs — full request/response tracing for a UI flow, plus dataflow edges between calls.
 *
 * WHY THIS EXISTS
 * The earlier capture recorded only {method, url, requestBody} for non-GET calls. That is enough
 * to reproduce a single create in isolation, but it cannot show how a flow actually works:
 *   - no response bodies, so a server-assigned id (addressId, resourceId) is never observed;
 *   - no GETs, so the reference-data lookups a form depends on are invisible;
 *   - no status codes, so a failed step inside a cascade looks identical to a successful one.
 * Consequently the Clients cascade was documented as four POSTs in a known order, but the claim
 * that the addresses response feeds the clients request was inference, never evidence.
 *
 * This records the complete exchange and then derives DATAFLOW EDGES: when a value that first
 * appeared in an earlier response shows up in a later request, that is a real dependency, and it
 * is exactly the material the flow graph needs.
 *
 * SECURITY: auth material is stripped before anything is written. Cookie / CSRF / Authorization
 * headers are dropped by name and never persisted.
 *
 *   node tools/cdp/trace.mjs clients
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import { goto, resetToGrid, clickButton, setFields } from './ext.mjs';
import { SPECS } from './capture2.mjs';

const OUT_DIR = 'knowlegde_graph/blue-yonder-sce/index/traces';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf|proxy-authorization)$/i;

const safeHeaders = (h) => Object.fromEntries(
  Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)),
);

/* Values worth tracking as identifiers. Short/common values produce noise, so require some
 * length and skip pure booleans/empties. */
const isIdish = (v) => typeof v === 'string' && v.length >= 3 && v.length <= 80
  && !/^(true|false|null|)$/i.test(v);

/* Walk any JSON structure and yield leaf scalars with their paths. */
function* leaves(obj, path = '') {
  if (obj === null || obj === undefined) return;
  if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) yield* leaves(obj[i], `${path}[${i}]`);
  } else if (typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) yield* leaves(v, path ? `${path}.${k}` : k);
  } else {
    yield { path, value: obj };
  }
}

const parse = (t) => { try { return JSON.parse(t); } catch { return null; } };

/*
 * Derive dependency edges: a value produced by call A's RESPONSE that later appears in call B's
 * REQUEST (body or URL). This is what turns a list of calls into a graph.
 */
export function deriveEdges(calls) {
  const produced = []; // {callIndex, path, value}
  const edges = [];
  calls.forEach((call, i) => {
    // Consume first: does this request use anything produced earlier?
    const reqBlobs = [];
    const rb = parse(call.request.body);
    if (rb) reqBlobs.push(['body', rb]);
    reqBlobs.push(['url', { url: call.request.url }]);
    for (const [where, blob] of reqBlobs) {
      for (const { path, value } of leaves(blob)) {
        if (!isIdish(value)) continue;
        for (const p of produced) {
          if (p.value !== value) continue;
          edges.push({
            from: { call: p.callIndex, endpoint: calls[p.callIndex].endpoint, field: p.path },
            to: { call: i, endpoint: call.endpoint, field: `${where}:${path}` },
            value,
          });
        }
      }
    }
    // Then publish what this response produced.
    const resBody = parse(call.response?.body || '');
    if (resBody) {
      for (const { path, value } of leaves(resBody)) {
        if (isIdish(value)) produced.push({ callIndex: i, path, value });
      }
    }
  });
  // Deduplicate: the same id often appears under several paths.
  const seen = new Set();
  return edges.filter((e) => {
    const k = `${e.from.call}->${e.to.call}:${e.value}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

async function traceSpec(key) {
  const spec = SPECS[key];
  if (!spec) throw new Error('unknown spec: ' + key);
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
    || browser.contexts()[0].pages()[0];

  const calls = [];
  const pending = new Map();
  // Calls are appended when the RESPONSE lands, which is not the order they were SENT. Cascade
  // ordering is a documented property of these flows, so record a monotonic request sequence and
  // sort by it before deriving edges - otherwise two in-flight requests can appear swapped.
  let reqSeq = 0;

  page.on('request', (req) => {
    if (!/\/data\/WM\//.test(req.url())) return;
    if (/webPerformanceEntries/.test(req.url())) return; // app telemetry, not a business call
    pending.set(req, {
      endpoint: req.url().split('/data/WM/')[1].split('?')[0],
      request: {
        method: req.method(),
        url: req.url(),
        query: Object.fromEntries(new URL(req.url()).searchParams),
        headers: safeHeaders(req.headers()),
        body: req.postData() || null,
      },
      seq: reqSeq++,
    });
  });

  page.on('response', async (res) => {
    const req = res.request();
    const rec = pending.get(req);
    if (!rec) return;
    pending.delete(req);
    let body = null;
    try { body = (await res.text()).slice(0, 20000); } catch { /* body may be unavailable */ }
    rec.response = { status: res.status(), headers: safeHeaders(res.headers()), body };
    calls.push(rec);
  });

  const out = { spec: key, resource: spec.resource };
  try {
    const frame = await goto(page, spec.route);
    await resetToGrid(page, frame);
    await page.waitForTimeout(1200);
    await clickButton(frame, page, { itemId: 'addButton' });
    await page.waitForTimeout(3800);
    const applied = await setFields(page, spec.fields, spec.pickFirst, spec.relax, spec.relaxRadio);
    out.applied = applied.applied;
    let invalid = applied.invalid;
    for (const phase of spec.pickPhases || []) {
      await page.waitForTimeout(2600);
      const r = await setFields(page, {}, phase, spec.relax, spec.relaxRadio);
      if (r && r.invalid) invalid = r.invalid;
    }
    out.invalid = invalid;
    if (invalid?.length) out.note = 'invalid before Save; not saving';
    else {
      await clickButton(frame, page, { itemId: 'saveButton' });
      await page.waitForTimeout(5500);
    }
  } catch (err) {
    out.error = String(err).split('\n')[0].slice(0, 180);
  }
  await page.waitForTimeout(1500);
  await browser.close();

  calls.sort((a, b) => a.seq - b.seq);
  out.calls = calls;
  out.writes = calls.filter((c) => c.request.method !== 'GET');
  out.edges = deriveEdges(calls);
  fs.mkdirSync(OUT_DIR, { recursive: true });
  fs.writeFileSync(`${OUT_DIR}/${key}.json`, JSON.stringify(out, null, 2) + '\n');
  return out;
}

const key = process.argv[2];
if (key) {
  const out = await traceSpec(key);
  console.log(JSON.stringify({
    spec: out.spec,
    totalCalls: out.calls.length,
    gets: out.calls.filter((c) => c.request.method === 'GET').length,
    writes: out.writes.map((c) => `${c.request.method} ${c.endpoint} -> ${c.response?.status}`),
    edges: out.edges.map((e) => `${e.from.endpoint}.${e.from.field} => ${e.to.endpoint}.${e.to.field}  (${e.value})`),
    invalid: out.invalid, note: out.note, error: out.error,
  }, null, 1));
}
