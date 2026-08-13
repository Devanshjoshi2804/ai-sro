/*
 * verify-writes.js — repeatable lifecycle verifier for write-endpoints.json
 *
 * WHY THIS EXISTS
 * write-endpoints.json is a claim ledger: 54 entries each asserting `verified: true`.
 * Every prior proof was a hand-run browser fetch written up as prose, so the ledger could
 * never be re-checked, and at least one entry (transportEquipmentTypes) was proven false
 * on 2026-08-12 by a GET against a route that does not exist. The proof method used then
 * — "confirmed via a separate GET returning 404 afterwards" — is CIRCULAR: a nonexistent
 * route 404s forever, so the check passes whether or not anything was ever deleted.
 *
 * This harness replaces that with machine-checked assertions that cannot pass vacuously.
 *
 * HOW TO RUN
 * Paste this whole file into the DevTools console of the Blue Yonder app tab, then:
 *     await verifyWrites.phase1()          // read-only: does each route even exist?
 *     await verifyWrites.phase2()          // full create -> read -> update -> delete cycle
 * It runs in the page origin, so the session cookie and CSRF token are picked up from the
 * live app. Nothing here ever reads, logs, or transmits either credential.
 *
 * THE 404 TAXONOMY (the core of the rigor upgrade)
 * This deployment returns two structurally different 404s, and conflating them is what let
 * a dead endpoint sit in the ledger marked verified:
 *   route missing  -> {"message":"Not Found","url":"/ws/wm/...","status":"404"}
 *   record missing -> {"timestamp":...,"responseId":...,"errors":[{"userMessage":...}]}
 * A delete is only proven by a RECORD-MISSING 404. A ROUTE-MISSING 404 proves the opposite:
 * the endpoint was never real.
 */
(() => {
  const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
  const app = () => {
    const f = document.querySelector('iframe');
    return f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
  };
  const csrf = () => {
    const w = app();
    const h = w.Ext && w.Ext.Ajax && w.Ext.Ajax.defaultHeaders;
    return (h && h['CSRF-ENCRYPT-TOKEN']) || null;
  };

  // Classify a response the way the executor must: status alone is not enough.
  const classify = (status, text) => {
    if (status >= 200 && status < 300) return 'OK';
    if (status === 404) {
      if (/"url"\s*:\s*"\/ws\//.test(text)) return 'ROUTE-MISSING';
      if (/"errors"\s*:/.test(text)) return 'RECORD-MISSING';
      return 'UNKNOWN-404';
    }
    return 'HTTP-' + status;
  };

  async function call(method, path, body) {
    const w = app();
    const token = csrf();
    const headers = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    // Writes require the app's CSRF header; a write without it returns a misleading empty 404.
    if (method !== 'GET' && token) headers['CSRF-ENCRYPT-TOKEN'] = token;
    const res = await w.fetch(BASE + path, {
      method,
      credentials: 'include',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch (e) { /* non-JSON body is itself a finding */ }
    return { status: res.status, kind: classify(res.status, text), json, text };
  }

  const unwrap = (r) => (r.json && 'data' in r.json ? r.json.data : r.json);
  const MARK = 'ZZVER';               // every record this harness creates carries this prefix
  const stamp = () => MARK + String(Date.now()).slice(-6);

  /*
   * FIXTURES — the executable form of what write-endpoints.json only states in prose.
   * Each entry is what an agent actually needs and cannot currently get from the ledger.
   *
   *   collection  path of the collection (route-existence probe target)
   *   make()      returns the create body; must produce a uniquely-named throwaway record
   *   id(rec)     derives the resource id from the created record (id shape is per-resource
   *               on this platform — there is no universal rule, so it is declared per fixture)
   *   put(rec)    returns {field, value} to mutate; PUT is tested against the record THIS
   *               harness created, never against real data, so blast radius stays at zero
   *   safe        false marks a resource we refuse to write to, with a stated reason.
   *               Skips are declared here rather than silently omitted.
   */
  /*
   * WHAT THE 2026-08-12 RUN ESTABLISHED ABOUT PAYLOADS — read this before adding a fixture.
   *
   * A failing create returns 422 with errors[0].userMessage naming the missing DB COLUMN,
   * e.g. "Missing argument: Description (lngdsc)". That message is NOT enough to build a
   * working body: the API rejects the raw column name and wants a camelCase JSON key that
   * is not mechanically derivable from it.
   *
   *   resource       DB column in the 422    recipe said    key the API actually wants
   *   businessUnits  lngdsc                  description    businessUnitDescription
   *   locationTypes  loc_typ_cat             (undocumented) locationTypeCategory
   *
   * So payload discovery by API probing does not work on this platform. Two reliable routes:
   *   1. GET an existing record and read its keys (fails when the collection is empty).
   *   2. Capture the real request the UI sends — see captureUI() below. This is the only
   *      method that worked for businessUnits, which has zero rows.
   * This is exactly why a fixture must carry a captured payload rather than a prose note.
   */
  const FIXTURES = {
    clientGroups: {
      collection: '/wm/clientGroups',
      make: () => { const c = stamp(); return { clientGroup: c, clientGroupDescription: c + ' desc', adjustmentThresholdCost: 0, adjustmentThresholdUnit: 0, self_uri: '', clients_uri: '' }; },
      id: (r) => r.resourceId || r.clientGroup,
      put: () => ({ field: 'clientGroupDescription', value: 'verified-' + stamp() }),
    },
    customerTypes: {
      collection: '/wm/customerTypes',
      make: () => { const c = stamp(); return { customerType: c, description: c + ' desc' }; },
      id: (r) => r.resourceId || r.customerType,
      put: () => ({ field: 'description', value: 'verified-' + stamp() }),
    },
    transportModes: {
      collection: '/wm/transportModes',
      // NOT site-scoped: this collection 500s if given siteId/subsites.
      make: () => { const c = 'Z' + String(Date.now()).slice(-2); return { transportMode: c, transportModeDescription: c + ' desc', directFlag: 0, smallPackageFlag: 0, palletBuildConsolidationBy: '', warehouseId: '' }; },
      id: (r) => r.resourceId || r.transportMode,
      put: () => ({ field: 'transportModeDescription', value: 'verified-' + stamp() }),
    },
    equipmentTypes: {
      collection: '/wm/equipmentTypes',
      make: () => { const c = stamp(); return { equipmentType: c, description: c + ' desc' }; },
      id: (r) => r.resourceId || r.equipmentType,
      put: () => ({ field: 'description', value: 'verified-' + stamp() }),
    },
    // locationTypeCategory is required and was documented nowhere; resourceId comes back as a
    // bare server-assigned number, not a compound key.
    locationTypes: {
      collection: '/wm/locationTypes',
      make: () => { const c = stamp().slice(0, 8); return { locationType: c, locationTypeCategory: 'STORAGE', longDescription: c + ' desc' }; },
      id: (r) => r.resourceId,
      put: () => ({ field: 'longDescription', value: 'verified-' + stamp() }),
    },
    levelTypes: {
      collection: '/wm/levelTypes',
      make: () => { const c = stamp(); return { levelType: c, description: c + ' desc' }; },
      id: (r) => r.resourceId,
      put: () => ({ field: 'description', value: 'verified-' + stamp() }),
    },
    // Payload captured from the real UI Add form on 2026-08-12 (captureUI). `description`
    // and `longDescription` are both rejected despite the 422 naming column lngdsc.
    businessUnits: {
      collection: '/wm/businessUnits',
      make: () => { const c = stamp(); return { businessUnit: c, businessUnitDescription: c + ' desc', warehouseId: 'SG', areaCount: 0, itemCount: 0 }; },
      id: (r) => r.resourceId,
      put: () => ({ field: 'businessUnitDescription', value: 'verified-' + stamp() }),
    },
    carriers: {
      collection: '/wm/carriers',
      make: () => { const c = stamp(); return { carrierCode: c, carrierName: c + ' name' }; },
      id: (r) => r.resourceId,
      put: () => ({ field: 'carrierName', value: 'verified-' + stamp() }),
    },
    // transportEquipmentTypes is in the ledger as two verified endpoints. Phase 1 is expected
    // to show ROUTE-MISSING, which is the whole point of probing before writing.
    transportEquipmentTypes: {
      collection: '/wm/transportEquipmentTypes',
      make: () => { const c = stamp(); return { code: c, description: c }; },
      id: (r) => r.resourceId,
    },
    // Real, but backed by the generic shared code-list table rather than its own resource.
    codes: { collection: '/wm/codes', readOnlyProbe: true },

    printers: { collection: '/wm/printers', readOnlyProbe: true },
    devices: { collection: '/wm/devices', readOnlyProbe: true },
    suppliers: { collection: '/wm/suppliers', readOnlyProbe: true },
    clients: { collection: '/wm/clients', readOnlyProbe: true },
    customers: { collection: '/wm/customers', readOnlyProbe: true },
    addresses: { collection: '/wm/addresses', readOnlyProbe: true },
    clientWarehouse: { collection: '/wm/clientWarehouse', readOnlyProbe: true },
    packingConfigurations: { collection: '/wm/packingConfigurations', readOnlyProbe: true },
    carrierProNumbers: { collection: '/wm/carrierProNumbers', readOnlyProbe: true },
    carrierCrossReferences: { collection: '/wm/carrierCrossReferences', readOnlyProbe: true },
    areas: { collection: '/wm/areas', readOnlyProbe: true },
    buildings: { collection: '/wm/buildings', readOnlyProbe: true },
    warehouses: { collection: '/wm/warehouses', readOnlyProbe: true },
    locations: {
      collection: '/wm/locations',
      safe: false,
      skipReason: '25k+ real rows and a batch-create path; no throwaway target that is provably isolated from real inventory. Left to a dedicated pass.',
    },
  };

  // Phase 1 — read-only. Establishes which routes are real BEFORE any write is attempted.
  async function phase1() {
    const out = [];
    for (const [name, f] of Object.entries(FIXTURES)) {
      const r = await call('GET', f.collection + '?query=[]&offset=0&limit=1');
      out.push({
        resource: name,
        status: r.status,
        kind: r.kind,
        routeExists: r.kind !== 'ROUTE-MISSING',
      });
    }
    return out;
  }

  // Phase 2 — full lifecycle. Only runs against fixtures that can create a throwaway record.
  async function phase2(only) {
    const results = [];
    for (const [name, f] of Object.entries(FIXTURES)) {
      if (only && !only.includes(name)) continue;
      if (f.readOnlyProbe) continue;
      const rec = { resource: name, steps: [], verdict: null, createdId: null };

      if (f.safe === false) {
        rec.verdict = 'SKIPPED';
        rec.skipReason = f.skipReason;
        results.push(rec);
        continue;
      }

      try {
        // 1. CREATE
        const body = f.make();
        const c = await call('POST', f.collection, body);
        rec.steps.push({ step: 'POST', status: c.status, kind: c.kind });
        if (c.kind !== 'OK') { rec.verdict = 'CREATE-FAILED'; rec.detail = c.text.slice(0, 200); results.push(rec); continue; }

        const created = unwrap(c);
        const id = f.id(created);
        rec.createdId = id;
        const idPath = f.collection + '/' + encodeURIComponent(id);

        // 2. READ BACK — a create is not proven by its own response.
        const g1 = await call('GET', idPath);
        rec.steps.push({ step: 'GET-after-create', status: g1.status, kind: g1.kind });
        if (g1.kind !== 'OK') { rec.verdict = 'CREATE-NOT-READABLE'; results.push(rec); continue; }

        // 3. UPDATE against the record we just made, then confirm by a separate read.
        if (f.put) {
          const cur = unwrap(g1);
          const { field, value } = f.put(cur);
          const putBody = { ...cur, [field]: value };
          delete putBody.self_uri;
          const p = await call('PUT', idPath, putBody);
          rec.steps.push({ step: 'PUT', status: p.status, kind: p.kind, field });
          const g2 = await call('GET', idPath);
          const after = unwrap(g2);
          const persisted = after && after[field] === value;
          rec.steps.push({ step: 'GET-after-put', persisted, got: after ? after[field] : null });
          if (!persisted) rec.putSilentlyDropped = true;
        }

        // 4. DELETE
        const d = await call('DELETE', idPath);
        rec.steps.push({ step: 'DELETE', status: d.status, kind: d.kind });

        // 5. CONFIRM GONE — must be RECORD-MISSING. A ROUTE-MISSING here would mean the
        //    endpoint never existed and the whole cycle proved nothing.
        const g3 = await call('GET', idPath);
        rec.steps.push({ step: 'GET-after-delete', status: g3.status, kind: g3.kind });
        rec.verdict =
          g3.kind === 'RECORD-MISSING' ? 'PASS'
          : g3.kind === 'ROUTE-MISSING' ? 'CIRCULAR-PROOF-ROUTE-DEAD'
          : g3.kind === 'OK' ? 'DELETE-DID-NOT-DELETE'
          : 'INCONCLUSIVE';
      } catch (err) {
        rec.verdict = 'ERROR';
        rec.detail = String(err).slice(0, 200);
      }
      results.push(rec);
    }
    return results;
  }

  // Safety net: find anything this harness created and failed to clean up.
  async function sweep() {
    const found = [];
    for (const [name, f] of Object.entries(FIXTURES)) {
      const r = await call('GET', f.collection + '?query=[]&offset=0&limit=500');
      if (r.kind !== 'OK') continue;
      const rows = unwrap(r);
      if (!Array.isArray(rows)) continue;
      rows.forEach((row) => {
        if (JSON.stringify(row).includes(MARK)) found.push({ resource: name, id: row.resourceId });
      });
    }
    return found;
  }

  /*
   * captureUI — the only reliable way to learn a create payload on this platform.
   *
   * Install it, then drive the screen's real Add form by hand (or with the browser tools) and
   * click Save. Every non-GET request the app makes is recorded with its exact body, which is
   * what belongs in the fixture and in write-endpoints.json.
   *
   *     verifyWrites.captureUI.install()
   *     // ... click Add, fill the form, click Save ...
   *     verifyWrites.captureUI.dump()
   *
   * This is what produced businessUnitDescription, a key neither the API's own 422 nor the
   * recipe could give us.
   */
  const captureUI = {
    install() {
      const w = app();
      w.__cap = [];
      if (w.__capInstalled) return 'already installed (log cleared)';
      const XHR = w.XMLHttpRequest;
      const oOpen = XHR.prototype.open, oSend = XHR.prototype.send;
      XHR.prototype.open = function (m, u) { this.__m = m; this.__u = u; return oOpen.apply(this, arguments); };
      XHR.prototype.send = function (b) {
        if (this.__m && this.__m !== 'GET') w.__cap.push({ method: this.__m, url: String(this.__u).split('?')[0], body: b ? String(b).slice(0, 2000) : null });
        return oSend.apply(this, arguments);
      };
      const of = w.fetch;
      w.fetch = function (u, o) {
        if (o && o.method && o.method !== 'GET') w.__cap.push({ method: o.method, url: String(u).split('?')[0], body: o.body ? String(o.body).slice(0, 2000) : null });
        return of.apply(this, arguments);
      };
      w.__capInstalled = true;
      return 'installed';
    },
    dump(filter) {
      const w = app();
      const all = w.__cap || [];
      return filter ? all.filter((c) => c.url.includes(filter)) : all;
    },
  };

  window.verifyWrites = { phase1, phase2, sweep, captureUI, call, classify, unwrap, FIXTURES, MARK };
  return 'verifyWrites ready: phase1() | phase2() | sweep() | captureUI.install()/.dump()';
})();
