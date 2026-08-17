/*
 * describe.mjs — READ-ONLY. Open each screen's Add form and dump its real field model.
 *
 * WHY THIS IS THE IMPORTANT TOOL
 * The expensive part of documenting a write endpoint is not the write, it is learning what the
 * body has to contain. Neither source we had works:
 *   - write-endpoints.json stores create bodies as English prose inside `notes`.
 *   - The API's own 422 names the missing DB COLUMN (`lngdsc`), but rejects that name in the
 *     body and wants a camelCase key that is not derivable from it (`businessUnitDescription`).
 * The ExtJS form model has both halves — the visible label AND the JSON field name the app will
 * actually send — and reading it requires no write, no record, and no cleanup.
 *
 * It also surfaces constraints that cost several failed attempts to find by probing, e.g.
 * equipmentTypes needing four required fields with voiceCode numeric, 2 chars, and globally
 * unique, and levelTypes labelling its key field "Name" rather than "Level Type".
 *
 * Screens whose collection is EMPTY can only be solved this way — there is no existing record to
 * sample keys from.
 *
 *   node tools/cdp/describe.mjs            # every screen below
 *   node tools/cdp/describe.mjs suppliers  # one screen
 */
import { chromium } from 'playwright';

const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

export const ROUTES = {
  suppliers: '#wm.config/wm.config.partners.suppliers////',
  clients: '#wm.config/wm.config.partners.clients////',
  customers: '#wm.config/wm.config.partners.customers.main////',
  carriers: '#wm.config/wm.config.partners.carriers.main////',
  carrierProNumbers: '#wm.config/wm.config.partners.carriers.carrierpronumber////',
  carrierCrossReferences: '#wm.config/wm.config.partners.carriers.crossreferences////',
  transportModes: '#wm.config/wm.config.partners.carriers.transportmodes////',
  customerTypes: '#wm.config/wm.config.partners.customers.types////',
  clientGroups: '#wm.config/wm.config.partners.clients////',
  businessUnits: '#wm.config/wm.config.warehouse.businessunits////',
  buildings: '#wm.config/wm.config.warehouse.buildings////',
  areas: '#wm.config/wm.config.warehouse.areas////',
  locationTypes: '#wm.config/wm.config.warehouse.locations.locationtypes////',
  levelTypes: '#wm.config/wm.config.warehouse.locations.leveltypes////',
  equipmentTypes: '#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////',
  locationAccessGroups: '#wm.config/wm.config.equipment.equipment.locationaccessgroups////',
  transportEquipmentType: '#wm.config/wm.config.equipment.equipment.transportequipmenttype////',
  printers: '#wm.config/wm.config.equipment.hardware.printers////',
  rfDevices: '#wm.config/wm.config.equipment.hardware.rfdevices////',
  voiceDevices: '#wm.config/wm.config.equipment.hardware.voicedevices////',
  workstations: '#wm.config/wm.config.equipment.hardware.workstations////',
};

const appFrame = async (page) => {
  for (let i = 0; i < 30; i++) {
    const f = page.frames().find((fr) => fr.url().includes('jdadelivers') && fr !== page.mainFrame());
    if (f) return f;
    await page.waitForTimeout(500);
  }
  return page.mainFrame();
};

/* Hash routing, never page.goto: a full load drops this app's OIDC session, and re-navigating to
 * an already-current hash is a router no-op that would strand us on the previous Add form. */
async function goto(page, route) {
  await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
  await page.waitForTimeout(2000);
  await page.evaluate((h) => { window.location.hash = h; }, route);
  await page.waitForTimeout(4500);
  return appFrame(page);
}

async function clickVisible(frame, text, timeout = 12000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const all = frame.getByText(text, { exact: true });
    const n = await all.count().catch(() => 0);
    for (let i = 0; i < n; i++) {
      const el = all.nth(i);
      if (await el.isVisible().catch(() => false)) {
        const b = await el.boundingBox().catch(() => null);
        if (b && b.width > 0 && b.height > 0) { await el.click(); return true; }
      }
    }
    await frame.page().waitForTimeout(400);
  }
  return false;
}

/* Read the live ExtJS form model: JSON field name, visible label, required flag, control type. */
const readForm = (page) => page.evaluate(() => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  const forms = w.Ext.ComponentQuery.query('form');
  if (!forms.length) return { error: 'no form rendered' };
  const form = forms[forms.length - 1];
  const fields = form.getForm().getFields().items.map((x) => ({
    field: x.name,
    label: x.fieldLabel || null,
    required: x.allowBlank === false,
    type: x.xtype,
    value: typeof x.getValue === 'function' ? x.getValue() : null,
    maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
  }));
  return { total: fields.length, required: fields.filter((x) => x.required), all: fields };
});

export async function describe(page, key) {
  const route = ROUTES[key];
  const out = { screen: key, route };
  try {
    const frame = await goto(page, route);
    if (!(await clickVisible(frame, 'Add'))) { out.error = 'no visible Add button'; return out; }
    await page.waitForTimeout(3500);
    Object.assign(out, await readForm(page));
    // Leave the form without saving so nothing is created and the next screen starts clean.
    await clickVisible(frame, 'Cancel', 4000);
    await page.waitForTimeout(1200);
  } catch (err) {
    out.error = String(err).split('\n')[0].slice(0, 160);
  }
  return out;
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];
const keys = process.argv[2] ? [process.argv[2]] : Object.keys(ROUTES);
const results = [];
for (const k of keys) {
  const r = await describe(page, k);
  results.push(r);
  console.error(`${k}: ${r.error ? 'ERR ' + r.error : (r.required || []).length + ' required / ' + r.total + ' fields'}`);
}
console.log(JSON.stringify(results, null, 1));
await browser.close();
