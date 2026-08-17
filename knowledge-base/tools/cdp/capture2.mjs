/*
 * capture2.mjs — capture create payloads by driving forms through the ExtJS field model.
 *
 * WHY NOT DOM LABELS (what capture.mjs did)
 * Label-based .fill() only works on plain textfields. These forms are mostly combos, lookups and
 * wmAddress composites, which ignore typed text unless the underlying model value is set — the
 * same failure already documented on Carrier PRO Number, where typing a real carrier code fills
 * the box visually but leaves the model null and Save then does nothing at all, silently.
 *
 * So we address fields by their JSON field NAME (from index/form-models.json, captured read-only
 * by describe.mjs) and set them through the form's own API. The app's normal Save path then runs
 * untouched, and page.on('request') records the exact body it sends — which is the artifact
 * write-endpoints.json was missing.
 *
 *   node tools/cdp/capture2.mjs workstations
 */
import { chromium } from 'playwright';

const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

/*
 * Each spec sets fields by JSON name. Values are chosen to satisfy the maxLength and type
 * constraints reported by describe.mjs, and every code is ZV-prefixed so the sweep can find
 * anything left behind.
 */
export const SPECS = {
  workstations: {
    route: '#wm.config/wm.config.equipment.hardware.workstations////',
    resource: 'devices',
    fields: { deviceCode: 'ZVW1', deviceName: 'ZV capture' },
  },
  voiceDevices: {
    route: '#wm.config/wm.config.equipment.hardware.voicedevices////',
    resource: 'devices',
    // localeId is a combo: pick whatever the bound store already offers rather than guessing.
    fields: { deviceCode: 'ZVV1', deviceName: 'ZV capture' },
    pickFirst: ['localeId'],
  },
  printers: {
    route: '#wm.config/wm.config.equipment.hardware.printers////',
    resource: 'printers',
    // "Printer Name" is printerAddress and "Printer Description" is printerName — inverted
    // labels, which is what made the recorded id shape look wrong.
    fields: { printerAddress: 'ZVP1', printerName: 'ZV cap' },
    pickFirst: ['printerType'],
    // Printer Status is a radiogroup with no field name; it must be explicitly selected.
    relaxRadio: ['Printer Status'],
  },
  clients: {
    route: '#wm.config/wm.config.partners.clients////',
    resource: 'clients',
    // One UI create here cascades to four resources: addresses, clients, clientWarehouse,
    // packingConfigurations — so this single capture covers four ledger entries.
    fields: { clientId: 'ZVCL1', addressName: 'ZV Capture Addr' },
  },
  // Duplicate-key probes: re-test, under Playwright with full request+response capture, the
  // claims originally made in hand-driven Claude-in-Chrome sessions. clients.md asserts this
  // cascade is NOT atomic and leaves a real orphan address on every failed attempt.
  clientsDuplicate: {
    route: '#wm.config/wm.config.partners.clients////',
    resource: 'clients',
    fields: { clientId: '----', addressName: { addressName: 'ZV Dup Probe Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' } },
    relax: ['addressName'],
  },
  // The remaining hand-asserted claims, each re-driven through the real UI with full capture.
  customersDuplicate: {
    route: '#wm.config/wm.config.partners.customers.main////',
    resource: 'customers',
    // existing-customers.md: "duplicate Customer number is a CLIENT-SIDE gate, zero requests fire".
    fields: { customerNumber: '0000000040', addressName: { addressName: 'ZV Dup Cust Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' } },
    pickFirst: ['clientId', 'customerType'],
    relax: ['addressName'],
  },
  carriersDuplicate: {
    route: '#wm.config/wm.config.partners.carriers.main////',
    resource: 'carriers',
    // carriers.md: duplicate is SERVER-side, surfaced as a "Record already exists" modal.
    fields: { carrierCode: '001', carrierName: 'ZV dup probe' },
  },
  transportModesDuplicate: {
    route: '#wm.config/wm.config.partners.carriers.transportmodes////',
    resource: 'transportModes',
    // carriers.md: duplicate is CLIENT-side, zero network calls.
    fields: { transportMode: 'AF', transportModeDescription: 'ZV dup probe' },
  },
  ccrDuplicate: {
    route: '#wm.config/wm.config.partners.carriers.crossreferences////',
    resource: 'carrierCrossReferences',
    // carriers.md: duplicate composite key blocked CLIENT-side with a readable message.
    fields: { carrier: 'FDE2', serviceLevel: 'FDE2', destinationName: 'ENVEYO' },
  },
  suppliersDuplicate: {
    route: '#wm.config/wm.config.partners.suppliers////',
    resource: 'suppliers',
    // suppliers.md asserts a clean 409 with NO address POST fired, i.e. no orphan.
    fields: { supplierNumber: '0040381130715', addressName: { addressName: 'ZV Dup Probe Addr2', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' } },
    pickFirst: ['clientId'],
    relax: ['addressName'],
  },
  suppliers: {
    route: '#wm.config/wm.config.partners.suppliers////',
    resource: 'suppliers',
    fields: { supplierNumber: 'ZVS1', addressName: { addressName: 'ZV Capture Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' } },
    pickFirst: ['clientId'],
    relax: ['addressName'],
  },
  customers: {
    route: '#wm.config/wm.config.partners.customers.main////',
    resource: 'customers',
    fields: { customerNumber: 'ZVCU1', addressName: { addressName: 'ZV Capture Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' } },
    // customerType is the documented conditional-required trap on this screen: with it blank
    // and Cross Dock / Pallet Building left on "Inherit", Save is absorbed by an invisible
    // modal mask - no error, no request, and the form reports zero invalid fields.
    pickFirst: ['clientId', 'customerType'],
    relax: ['addressName'],
  },
  carrierProNumbers: {
    route: '#wm.config/wm.config.partners.carriers.carrierpronumber////',
    resource: 'carrierProNumbers',
    // The known-broken screen: Carrier is a carrierLookup and Carrier Facility Address a
    // wmAddress. Typing into either fills the box but leaves the model null, and Save then
    // produces no error, no modal and no request at all. Set the models directly instead.
    fields: {
      addressName: { addressName: 'ZV Pro Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' },
    },
    pickFirst: ['carrier'],
    relax: ['addressName', 'carrier'],
  },
  carrierCrossReferences: {
    route: '#wm.config/wm.config.partners.carriers.crossreferences////',
    resource: 'carrierCrossReferences',
    // All three required fields are combos; a duplicate composite key is rejected client-side,
    // so the picks must not collide with an existing row.
    fields: {},
    // Carrier first; Service Level's store is populated only once a carrier is selected.
    pickFirst: ['carrier'],
    pickPhases: [['serviceLevel'], ['destinationName']],
  },
};

const appFrame = async (page) => {
  for (let i = 0; i < 30; i++) {
    const f = page.frames().find((fr) => fr.url().includes('jdadelivers') && fr !== page.mainFrame());
    if (f) return f;
    await page.waitForTimeout(500);
  }
  return page.mainFrame();
};

async function goto(page, route) {
  await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
  await page.waitForTimeout(2000);
  await page.evaluate((h) => { window.location.hash = h; }, route);
  await page.waitForTimeout(4500);
  return appFrame(page);
}

/* Stale ExtJS components persist in the DOM, so always click a genuinely visible, sized node. */
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

/* Set values through the form's own API, and for combos take a real option from the bound store
 * so the model value is one the server will accept. Returns per-field outcomes plus whatever is
 * still invalid, which is the fastest way to see why a Save will not fire. */
const applyFields = (page, fields, pickFirst) => page.evaluate(({ fields, pickFirst }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  const forms = w.Ext.ComponentQuery.query('form');
  if (!forms.length) return { error: 'no form' };
  const form = forms[forms.length - 1].getForm();
  const applied = {};
  for (const [name, value] of Object.entries(fields || {})) {
    const fld = form.findField(name);
    if (!fld) { applied[name] = 'FIELD-NOT-FOUND'; continue; }
    fld.setValue(value);
    applied[name] = fld.getValue();
  }
  for (const name of pickFirst || []) {
    const fld = form.findField(name);
    if (!fld) { applied[name] = 'FIELD-NOT-FOUND'; continue; }
    const store = fld.getStore && fld.getStore();
    const rec = store && store.getCount && store.getCount() > 0 ? store.getAt(0) : null;
    if (!rec) { applied[name] = 'EMPTY-STORE'; continue; }
    fld.setValue(rec.get(fld.valueField || 'code'));
    applied[name] = fld.getValue();
  }
  const invalid = form.getFields().items
    .filter((x) => x.allowBlank === false && !x.isValid())
    .map((x) => ({ field: x.name, label: x.fieldLabel, errors: x.getErrors ? x.getErrors() : null }));
  return { applied, invalid };
}, { fields, pickFirst });

export async function run(key) {
  const spec = SPECS[key];
  if (!spec) throw new Error('unknown spec: ' + key);
  const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
  const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
    || browser.contexts()[0].pages()[0];
  const out = { spec: key, resource: spec.resource, requests: [] };

  page.on('request', (req) => {
    // The app's own telemetry batch is a POST but not a business write; counting it made an
    // earlier failed create report success.
    if (req.method() !== 'GET' && !/webPerformanceEntries/.test(req.url()) && /\/data\/WM\/wm\//.test(req.url())) {
      out.requests.push({ method: req.method(), url: req.url().split('?')[0], body: req.postData() });
    }
  });

  try {
    const frame = await goto(page, spec.route);
    if (!(await clickVisible(frame, 'Add'))) throw new Error('no visible Add');
    await page.waitForTimeout(3500);
    Object.assign(out, await applyFields(page, spec.fields, spec.pickFirst));
    await page.waitForTimeout(600);
    if (out.invalid && out.invalid.length) {
      out.note = 'still invalid before Save — not clicking Save';
    } else {
      await clickVisible(frame, 'Save');
      await page.waitForTimeout(4500);
    }
    out.ok = out.requests.some((r) => r.method === 'POST');
  } catch (err) {
    out.error = String(err).split('\n')[0].slice(0, 180);
  }
  await browser.close();
  return out;
}

// Only run as a CLI when invoked directly; importing SPECS must not execute a capture.
const isEntry = process.argv[1] && process.argv[1].endsWith('capture2.mjs');
if (isEntry && process.argv[2]) console.log(JSON.stringify(await run(process.argv[2]), null, 1));
