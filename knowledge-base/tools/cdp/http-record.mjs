/*
 * http-record.mjs — record COMPLETE HTTP exchanges into knowlegde_graph/blue-yonder-sce/http/.
 *
 * Prior tooling recorded {method, url, requestBody} for writes only. That cannot answer the
 * questions that matter: what status did the server return, what did it return in the body, which
 * ids did it assign, and what happens on the error paths. Everything here stores the full
 * request AND full response so a claim can be checked against a recorded exchange rather than a
 * sentence someone wrote.
 *
 * Auth is never persisted: the fetch runs inside the authenticated page, so this process never
 * sees a cookie or token, and sensitive headers are stripped by name before writing.
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

export const HTTP_DIR = 'knowlegde_graph/blue-yonder-sce/http';
export const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;

export const stripAuth = (h) => Object.fromEntries(
  Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)),
);

export async function connect() {
  const browser = await chromium.connectOverCDP('http://localhost:9222');
  const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers/portal'))
    || browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
    || browser.contexts()[0].pages()[0];
  return { browser, page };
}

/*
 * Perform one call inside the page and return the whole exchange.
 * `kind` distinguishes the two 404 shapes this deployment emits; see knowlegde_graph/SCHEMA.md.
 */
export const exchange = (page, method, urlPath, body) => page.evaluate(
  async ({ method, urlPath, body, base }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body !== undefined && body !== null) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;

    let res, text = '', netErr = null;
    try {
      res = await w.fetch(base + urlPath, {
        method, credentials: 'include', headers,
        body: body === undefined || body === null ? undefined : JSON.stringify(body),
      });
      text = await res.text();
    } catch (e) {
      netErr = String(e).slice(0, 200);
    }
    if (!res) return { networkError: netErr, requestHeaders: headers };

    const respHeaders = {};
    res.headers.forEach((v, k) => { respHeaders[k] = v; });
    let kind = 'OK';
    if (res.status === 404) {
      kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING'
        : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    } else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;

    let parsed = null;
    try { parsed = JSON.parse(text); } catch { /* keep raw */ }
    return {
      requestHeaders: headers,
      status: res.status,
      statusText: res.statusText,
      responseHeaders: respHeaders,
      bodyRaw: parsed ? null : text.slice(0, 4000),
      body: parsed,
      kind,
    };
  },
  { method, urlPath, body, base: BASE },
);

/* Append one exchange record. Files are JSONL so they stay appendable and greppable. */
export function record(resource, rec) {
  const dir = path.join(HTTP_DIR, 'exchanges');
  fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(path.join(dir, `${resource}.jsonl`), JSON.stringify(rec) + '\n');
}

/* Run one probe and persist the whole exchange. */
export async function probe(page, { resource, caseName, method, urlPath, body, notes }) {
  const r = await exchange(page, method, urlPath, body);
  const rec = {
    ts: new Date().toISOString(),
    tool: 'tools/cdp/http-record.mjs',
    case: caseName,
    request: {
      method,
      url: urlPath.split('?')[0],
      query: Object.fromEntries(new URLSearchParams(urlPath.split('?')[1] || '')),
      headers: stripAuth(r.requestHeaders),
      body: body ?? null,
    },
    response: r.networkError ? { networkError: r.networkError } : {
      status: r.status,
      statusText: r.statusText,
      headers: stripAuth(r.responseHeaders),
      body: r.body,
      bodyRaw: r.bodyRaw,
      kind: r.kind,
    },
    notes: notes || null,
  };
  record(resource, rec);
  return rec;
}

/* Compact one-line view for console output. */
export const summarize = (rec) => `${rec.case}: ${rec.request.method} ${rec.request.url} -> `
  + (rec.response.networkError ? `NETERR ${rec.response.networkError}`
    : `${rec.response.status} ${rec.response.kind}`);

// Entry-guard: importing this module must never execute a request from another script's argv.
const isEntry = process.argv[1] && process.argv[1].endsWith('http-record.mjs');
if (isEntry && process.argv[3]) {
  const [method, urlPath] = process.argv.slice(2);
  const { browser, page } = await connect();
  const rec = await probe(page, { resource: 'adhoc', caseName: 'adhoc', method: method.toUpperCase(), urlPath });
  console.log(JSON.stringify(rec, null, 2));
  await browser.close();
}
