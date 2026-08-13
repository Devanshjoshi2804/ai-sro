#!/usr/bin/env node
// Regenerates knowlegde_graph/blue-yonder-sce/index/coverage.json — per-screen knowledge coverage tracker.
// Pure file analysis: reads app-map / form-models / write-endpoints / http exchanges, writes coverage.json, prints a table.
import fs from 'node:fs';
import path from 'node:path';

const ROOT = 'knowlegde_graph/blue-yonder-sce';
const IDX = path.join(ROOT, 'index');
const OUT = path.join(IDX, 'coverage.json');

function loadJSON(p, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    console.error(`WARN: could not read/parse ${p}: ${e.message}`);
    return fallback;
  }
}

function loadJSONL(p) {
  let text;
  try {
    text = fs.readFileSync(p, 'utf8');
  } catch {
    return null; // file missing
  }
  const rows = [];
  for (const line of text.trim().split('\n')) {
    if (!line) continue;
    try {
      rows.push(JSON.parse(line));
    } catch (e) {
      console.error(`WARN: bad jsonl line in ${p}: ${e.message}`);
    }
  }
  return rows;
}

const appMap = loadJSON(path.join(IDX, 'app-map.json'), { screens: [] });
const screens = appMap.screens || [];

const formModels = loadJSON(path.join(IDX, 'form-models-all.json'), { forms: [] });
const formsByHash = new Map((formModels.forms || []).map((f) => [f.hash, f]));

const writeEndpoints = loadJSON(path.join(IDX, 'write-endpoints.json'), []);
const writeByResource = new Map(); // resource -> { verifiedWithPayload: bool, endpoints: [...] }
for (const e of writeEndpoints) {
  if (!e.resource) continue;
  const cur = writeByResource.get(e.resource) || { verifiedWithPayload: false, endpoints: [] };
  cur.endpoints.push(e);
  if (e.verified && e.payload) cur.verifiedWithPayload = true;
  writeByResource.set(e.resource, cur);
}

// exchanges/<resource>.jsonl -> { hasGetBody: bool, cases: Set }
const exchangesDir = path.join(ROOT, 'http', 'exchanges');
const exchangesByResource = new Map();
if (fs.existsSync(exchangesDir)) {
  for (const file of fs.readdirSync(exchangesDir)) {
    if (!file.endsWith('.jsonl')) continue;
    const resource = file.slice(0, -'.jsonl'.length);
    const rows = loadJSONL(path.join(exchangesDir, file)) || [];
    const cases = new Set();
    let hasGetBody = false;
    for (const r of rows) {
      if (r.case) cases.add(r.case);
      if (r.request?.method === 'GET' && r.response?.body != null) hasGetBody = true;
    }
    exchangesByResource.set(resource, { hasGetBody, cases });
  }
}

const REQUIRED_FAILURE_CASES = ['create-duplicate', 'create-empty', 'confirm-gone'];

function computeScreen(s) {
  const resources = s.resources || [];
  const writable = !!(s.can_create || s.can_delete);

  // 1. structure
  const hasGridCols = (s.grids || []).some((g) => (g.columns || []).length > 0);
  const hasForms = (s.forms || []).length > 0;
  const hasActions = (s.actions || []).length > 0;
  const structure = hasGridCols || hasForms || hasActions;

  // 2. form_model
  let form_model;
  if (!s.can_create) {
    form_model = 'n/a';
  } else {
    const fm = formsByHash.get(s.hash);
    form_model = !!(fm && !fm.error && (fm.field_count || 0) > 0);
  }

  // 3. read_apis
  const read_apis = resources.length > 0;

  // 4. read_shapes: per-resource, do we have a recorded GET response body?
  let read_shapes;
  let read_shapes_detail = {};
  if (resources.length === 0) {
    read_shapes = 'n/a';
  } else {
    for (const r of resources) {
      read_shapes_detail[r] = !!exchangesByResource.get(r)?.hasGetBody;
    }
    read_shapes = Object.values(read_shapes_detail).every(Boolean);
  }

  // resources this screen actually WRITES to (read-resources ∩ known write-endpoint resources)
  const writeResources = resources.filter((r) => writeByResource.has(r));

  // 5. write_apis
  let write_apis;
  if (!writable) {
    write_apis = 'n/a';
  } else if (writeResources.length === 0) {
    write_apis = false; // screen claims create/delete but no write endpoint evidence for any of its resources
  } else {
    write_apis = writeResources.every((r) => writeByResource.get(r).verifiedWithPayload);
  }

  // 6. failure_modes
  let failure_modes;
  let failure_modes_detail = {};
  if (!writable) {
    failure_modes = 'n/a';
  } else if (writeResources.length === 0) {
    failure_modes = false;
  } else {
    for (const r of writeResources) {
      const cases = exchangesByResource.get(r)?.cases || new Set();
      failure_modes_detail[r] = REQUIRED_FAILURE_CASES.every((c) => cases.has(c));
    }
    failure_modes = Object.values(failure_modes_detail).every(Boolean);
  }

  const dimensions = { structure, form_model, read_apis, read_shapes, write_apis, failure_modes };
  const missing = Object.entries(dimensions)
    .filter(([, v]) => v === false)
    .map(([k]) => k);

  return {
    hash: s.hash,
    label: s.label,
    area: s.area,
    tier: s.tier,
    can_create: !!s.can_create,
    dimensions,
    missing,
    detail: {
      resources,
      write_resources: writeResources,
      read_shapes: read_shapes_detail,
      failure_modes: failure_modes_detail,
    },
  };
}

const screenResults = screens.map(computeScreen);

const DIMS = ['structure', 'form_model', 'read_apis', 'read_shapes', 'write_apis', 'failure_modes'];

function freshCounts() {
  const c = {};
  for (const d of DIMS) c[d] = { true: 0, false: 0, 'n/a': 0 };
  return c;
}

function tally(into, results) {
  for (const r of results) {
    for (const d of DIMS) {
      const v = r.dimensions[d];
      into[d][v === true ? 'true' : v === false ? 'false' : 'n/a']++;
    }
  }
}

const totals = { screens: screenResults.length, dimensions: freshCounts() };
tally(totals.dimensions, screenResults);
totals.screens_fully_complete = screenResults.filter((r) =>
  DIMS.every((d) => r.dimensions[d] !== false)
).length;

const byArea = {};
for (const r of screenResults) {
  const area = r.area || 'unknown';
  if (!byArea[area]) byArea[area] = { screens: 0, dimensions: freshCounts() };
  byArea[area].screens++;
  tally(byArea[area].dimensions, [r]);
}

const coverage = {
  generated_by: 'tools/coverage.mjs',
  generated_at: new Date().toISOString(),
  definition:
    'Six booleans per screen measure how complete our recorded knowledge is, not how good the screen/feature is. ' +
    'structure: grid columns, forms, or actions were captured off the live UI. ' +
    'form_model: for create-capable screens, the Add form fields were captured with no error and at least one field (n/a if the screen has no create). ' +
    'read_apis: the screen is known to call at least one read (GET) resource. ' +
    'read_shapes: for every resource the screen reads, we have a recorded GET response body in http/exchanges (n/a if it reads no resources). ' +
    'write_apis: for every resource the screen actually writes to (its read resources intersected with write-endpoints.json), the write endpoint is verified and has a captured payload (n/a if the screen has neither create nor delete). ' +
    'failure_modes: for every write resource, http/exchanges/<resource>.jsonl has create-duplicate, create-empty, and confirm-gone cases recorded (n/a if the screen has neither create nor delete). ' +
    'A dimension is only ever true when the underlying file content was checked, never because a file merely exists.',
  totals,
  by_area: byArea,
  screens: screenResults,
};

fs.mkdirSync(IDX, { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(coverage, null, 2) + '\n');

// ---- stdout summary ----
function pct(n, d) {
  return d === 0 ? '-' : Math.round((100 * n) / d) + '%';
}

console.log(`\nWrote ${OUT}\n`);
console.log(`${screenResults.length} screens total, ${totals.screens_fully_complete} fully complete (all applicable dimensions true)\n`);

const header = ['area', 'n', ...DIMS];
const rows = [header];
for (const [area, a] of Object.entries(byArea).sort((x, y) => y[1].screens - x[1].screens)) {
  rows.push([
    area,
    String(a.screens),
    ...DIMS.map((d) => `${a.dimensions[d].true}/${a.screens}`),
  ]);
}
rows.push([
  'TOTAL',
  String(totals.screens),
  ...DIMS.map((d) => `${totals.dimensions[d].true}/${totals.screens}`),
]);

const widths = header.map((_, i) => Math.max(...rows.map((r) => r[i].length)));
for (const r of rows) {
  console.log(r.map((c, i) => c.padEnd(widths[i])).join('  '));
}

console.log('\nTop 20 closest-to-complete screens (most dimensions true, not all):\n');
const scored = screenResults
  .map((r) => ({
    r,
    trueCount: DIMS.filter((d) => r.dimensions[d] === true).length,
    applicable: DIMS.filter((d) => r.dimensions[d] !== 'n/a').length,
  }))
  .filter((x) => x.trueCount < x.applicable) // not already fully complete
  .sort((a, b) => b.trueCount - a.trueCount || a.r.missing.length - b.r.missing.length);

for (const { r, trueCount, applicable } of scored.slice(0, 20)) {
  console.log(`${trueCount}/${applicable}  ${r.area.padEnd(16)} ${r.label.padEnd(30)} missing: ${r.missing.join(', ')}`);
}
