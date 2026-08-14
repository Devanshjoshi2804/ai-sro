/*
 * probe-referer.mjs — is `Referer` load-bearing for authentication on this WMS?
 *
 * WHY: an executor replaying a captured call correctly refused to replay `Referer` — the captured
 * value names a page from a demonstration that is over — and every read came back 302 to the login
 * page while carrying a valid session. That is a claim about the server's auth filter, and this
 * base's rule is that a claim needs a stored exchange.
 *
 * Every probe in this base so far ran INSIDE the page, where the browser attaches a same-origin
 * Referer automatically. So the base has 266 exchanges and not one of them tests this. That is a
 * blind spot created by the instrument, which is the kind worth naming.
 *
 * Read-only: three GETs of the same collection, differing only in the referrer the request carries.
 *
 *   node tools/cdp/probe-referer.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const HTTP_DIR = 'knowlegde_graph/blue-yonder-sce/http';
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const URL_PATH = '/wm/businessUnits?query=[]&offset=0&limit=1&siteId=SG&subsites=----';

/*
 * `redirect: 'manual'` matters. Following the redirect would return 200 with a login page, which
 * reads as success to anything checking only the status — precisely how this failure hid.
 */
const CASES = [
  ['referer-default', 'client', 'Browser attaches a same-origin Referer. This is what every prior probe did, unknowingly.'],
  ['referer-none', 'no-referrer', 'What an out-of-browser executor sends when it declines to replay a captured Referer.'],
  ['referer-target', 'target', 'A Referer derived from the call being made rather than replayed from the demonstration.'],
];

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  const results = [];
  for (const [name, mode, notes] of CASES) {
    const r = await page.evaluate(async ({ url, mode }) => {
      const f = document.querySelector('iframe');
      const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
      const init = { method: 'GET', credentials: 'include', headers: { Accept: 'application/json' }, redirect: 'manual' };
      if (mode === 'no-referrer') init.referrerPolicy = 'no-referrer';
      if (mode === 'target') { init.referrer = url; init.referrerPolicy = 'unsafe-url'; }
      let res, text = '';
      try { res = await w.fetch(url, init); text = await res.text(); }
      catch (e) { return { networkError: String(e).slice(0, 200) }; }
      const rh = {}; res.headers.forEach((v, k) => { rh[k] = v; });
      let parsed = null; try { parsed = JSON.parse(text); } catch {}
      return {
        status: res.status, type: res.type, redirected: res.redirected, url: res.url,
        headers: rh, body: parsed, bodyRaw: parsed ? null : text.slice(0, 400),
        looksLikeLogin: /login|signin|oauth|authorize/i.test(text.slice(0, 2000)) || /login|authorize/i.test(res.url),
      };
    }, { url: BASE + URL_PATH, mode });

    const rec = {
      ts: new Date().toISOString(), tool: 'tools/cdp/probe-referer.mjs', case: name,
      request: { method: 'GET', url: URL_PATH.split('?')[0], referer_mode: mode, headers: { accept: 'application/json' } },
      response: r.networkError ? { networkError: r.networkError }
        : { status: r.status, type: r.type, redirected: r.redirected, final_url: r.url, headers: r.headers, body: r.body, bodyRaw: r.bodyRaw, looks_like_login: r.looksLikeLogin },
      notes,
    };
    fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', 'businessUnits.jsonl'), JSON.stringify(rec) + '\n');
    results.push({ name, ...r });
    const n = Array.isArray(r.body?.data) ? r.body.data.length : 0;
    console.log(`  ${name.padEnd(18)} -> status=${r.status ?? 'ERR'} type=${r.type} rows=${n} login=${r.looksLikeLogin}`);
  }

  const withRef = results.find((x) => x.name === 'referer-default');
  const without = results.find((x) => x.name === 'referer-none');
  console.log(`\nVERDICT: ${withRef?.status === without?.status
    ? 'Referer is NOT load-bearing for this GET — both cases returned the same status.'
    : `Referer IS load-bearing: with=${withRef?.status}, without=${without?.status}.`}`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
