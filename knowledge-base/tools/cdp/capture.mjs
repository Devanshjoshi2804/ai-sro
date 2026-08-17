/*
 * capture.mjs — drive the real Blue Yonder UI over CDP and capture what it actually sends.
 *
 * WHY
 * write-endpoints.json marks 20 POST endpoints "verified" but stores each create body only as
 * English prose inside `notes`, so an agent cannot execute a single create from it. Worse, the
 * payload cannot be derived from the API either: a failed create returns 422 naming the missing
 * DB COLUMN, but the API rejects that column name in the body and wants a camelCase JSON key
 * that is not mechanically derivable from it (businessUnits: column `lngdsc`, recipe said
 * `description`, real key is `businessUnitDescription`).
 *
 * The only reliable source of truth is the request the app itself sends. This script drives the
 * real Add form and records that request.
 *
 * WHY CDP RATHER THAN A FRESH BROWSER
 * This app's OIDC/Keycloak session is the fragile part — a plain reload has dropped it before.
 * We attach to an already-authenticated Chrome instead of launching our own, so login happens
 * once, by hand, and every run after that reuses it.
 *
 * SETUP
 *   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
 *     --remote-debugging-port=9222 --user-data-dir=<throwaway profile> \
 *     "https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----"
 *   ...sign in by hand once...
 *   node tools/cdp/capture.mjs <screenKey>
 */
import { chromium } from 'playwright';

const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com';
const PORTAL = BASE + '/portal?siteId=SG&subsite=----';

/*
 * SCREENS — one entry per Add form we need a payload for.
 * `values` maps visible field LABEL -> value. Labels are used rather than CSS selectors because
 * ExtJS ids are generated and unstable across renders, while the label text is what the screen
 * actually shows and what the recipes document.
 * Every code value is prefixed ZV so the cleanup sweep can find anything left behind.
 */
export const SCREENS = {
  customerTypes: {
    route: '#wm.config/wm.config.partners.customers.types////',
    resource: 'customerTypes',
    // csttyp truncates at 4 chars — proven by a 422 on a longer value.
    values: { 'Customer Type': 'ZVC1', 'Customer Type Description': 'ZV capture' },
  },
  equipmentTypes: {
    route: '#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////',
    resource: 'equipmentTypes',
    // Four required fields, not two. API probing stalled here (422 on vehtyp_id, then
    // "Server error."); the form model gave the real set: vehicleTypeId, longDescription,
    // voiceCode, vehicleLimit.
    values: {
      'Warehouse Equipment Type': 'ZVE1',
      Description: 'ZV capture',
      // voiceCode is NUMERIC and truncates to 2 chars: 'ZVE1' arrived as 'E1' and failed with
      // "E1 is not a valid number". Neither constraint is documented anywhere in the ledger.
      // voiceCode must also be UNIQUE across all equipment types ("The voice code already
      // existed") — a second uniqueness constraint beyond the primary key, undocumented. 11 is
      // the lowest unused value in this environment.
      'Voice Code': '11',
      'LPN Warehouse Equipment Type Limit': '1',
    },
  },
  levelTypes: {
    route: '#wm.config/wm.config.warehouse.locations.leveltypes////',
    resource: 'levelTypes',
    // Collection is empty, so keys cannot be sampled from an existing record — UI capture is
    // the only route. Probing produced a 3-deep required chain: lvl_type_name, maxwgt, tot_lvl_units.
    // Label is "Name" (-> levelTypeName), not "Level Type". totalLevelUnits defaults to 1.
    // totalLevelUnits shows a default of 1 but loses it on re-render, so set it explicitly.
    values: { Name: 'ZVL1', Description: 'ZV capture', 'Total Level Units': '1' },
  },
};

const connect = async () => {
  const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => p.url().includes('jdadelivers')) || ctx.pages()[0];
  return { browser, page };
};

const isLoggedIn = (page) => page.url().includes('jdadelivers.com/portal');

/* The app renders inside an iframe; form controls live there, not in the top document. */
const appFrame = async (page) => {
  for (let i = 0; i < 30; i++) {
    const f = page.frames().find((fr) => fr.url().includes('jdadelivers') && fr !== page.mainFrame());
    if (f) return f;
    await page.waitForTimeout(500);
  }
  return page.mainFrame();
};

/*
 * Navigate by driving the SPA's own hash router, NOT page.goto().
 *
 * Two reasons:
 *  1. A full page load on this app has dropped the OIDC session before, forcing a manual
 *     re-login. Hash routing stays inside the authenticated session.
 *  2. page.goto() to a URL whose hash already matches is a no-op for the router, so a previous
 *     run left stranded on an Add form never returns to the grid — the failure mode that made
 *     the second run report 'no visible "Add"'.
 *
 * Bouncing through a neutral route guarantees a hash change even when the target route is
 * already current, and gets us off any half-filled form.
 */
async function goto(page, route) {
  const neutral = '#wm.config/wm.config.warehouse.warehouse////';
  await page.evaluate((h) => { window.location.hash = h; }, neutral);
  await page.waitForTimeout(2500);
  await page.evaluate((h) => { window.location.hash = h; }, route);
  await page.waitForTimeout(4500);
  return appFrame(page);
}

/*
 * Click the first VISIBLE element matching `text`.
 *
 * Necessary because this app leaves stale ExtJS component instances in the DOM: the Customer
 * Type Add form matches "Save" four times, three of them detached with a zero-size rect. A
 * plain .first() picks a dead one and times out, which is exactly what happened on the first run.
 */
async function clickVisible(frame, text, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const all = frame.getByText(text, { exact: true });
    const n = await all.count().catch(() => 0);
    for (let i = 0; i < n; i++) {
      const el = all.nth(i);
      if (await el.isVisible().catch(() => false)) {
        const box = await el.boundingBox().catch(() => null);
        if (box && box.width > 0 && box.height > 0) {
          await el.click();
          return true;
        }
      }
    }
    await frame.page().waitForTimeout(500);
  }
  throw new Error(`no visible "${text}" found within ${timeout}ms`);
}

/*
 * Fill by label. ExtJS renders <label>Text</label> beside an <input>, so we locate the label's
 * container and target the input within it rather than relying on `for`/`id` wiring, which this
 * app does not set consistently.
 */
async function fillByLabel(frame, label, value) {
  const strategies = [
    () => frame.getByLabel(label, { exact: false }).first(),
    () => frame.locator(`//label[contains(normalize-space(.),${JSON.stringify(label)})]/following::input[1]`).first(),
    () => frame.locator(`//*[contains(normalize-space(text()),${JSON.stringify(label)})]/following::input[1]`).first(),
  ];
  for (const make of strategies) {
    try {
      const el = make();
      await el.waitFor({ state: 'visible', timeout: 3000 });
      await el.fill(String(value));
      return true;
    } catch { /* try the next strategy */ }
  }
  return false;
}

export async function capture(key) {
  const spec = SCREENS[key];
  if (!spec) throw new Error('unknown screen: ' + key);
  const { browser, page } = await connect();
  const out = { screen: key, resource: spec.resource, requests: [], filled: {}, ok: false };

  if (!isLoggedIn(page)) {
    out.error = 'not authenticated — sign in manually in the CDP Chrome window first';
    await browser.close();
    return out;
  }

  // Native request capture: records the exact body the app sends, including on XHR.
  page.on('request', (req) => {
    // webPerformanceEntries is the app's own telemetry batch, not a business write. Counting
    // it as a POST made a failed create report ok:true on the first equipmentTypes run.
    const isTelemetry = /webPerformanceEntries/.test(req.url());
    if (req.method() !== 'GET' && !isTelemetry && /\/data\/WM\/wm\//.test(req.url())) {
      out.requests.push({ method: req.method(), url: req.url().split('?')[0], body: req.postData() });
    }
  });

  try {
    const frame = await goto(page, spec.route);
    await clickVisible(frame, 'Add');
    await page.waitForTimeout(3000);

    for (const [label, value] of Object.entries(spec.values)) {
      out.filled[label] = await fillByLabel(frame, label, value);
    }
    await page.waitForTimeout(800);

    // Save sits in a footer bar pinned outside the form's internal scroll region, so it is
    // reachable by role without scrolling the panel body.
    await clickVisible(frame, 'Save');
    await page.waitForTimeout(4000);
    out.ok = out.requests.some((r) => r.method === 'POST');
  } catch (err) {
    out.error = String(err).split('\n')[0].slice(0, 200);
  }
  await browser.close();
  return out;
}

const key = process.argv[2];
if (key) {
  const keys = key === 'all' ? Object.keys(SCREENS) : [key];
  for (const k of keys) console.log(JSON.stringify(await capture(k), null, 1));
}
