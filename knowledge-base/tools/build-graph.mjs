/*
 * build-graph.mjs — derive the flow graph from recorded evidence.
 *
 * WHAT THIS IS FOR
 * An agent driving this system needs to answer questions the flat catalogues cannot:
 *   "to create a supplier, what must exist first?"
 *   "if I POST /wm/addresses, which value from the response do I need next, and where?"
 *   "which screen writes this resource, and what else does that screen read first?"
 *   "what does this endpoint return when it fails?"
 *
 * EVERY EDGE CITES ITS EVIDENCE. The whole reason this knowledge base was rebuilt is that its
 * predecessor asserted relationships nobody could re-check, and four of those assertions turned
 * out to be false. So nothing is inferred from naming or convention here: an edge exists only
 * because a recorded exchange shows it, and each carries the file it came from.
 *
 * Inputs (all machine-generated):
 *   http/flows/*.json        UI call sequences with request+response
 *   http/exchanges/*.jsonl   per-resource probe batteries
 *   index/form-models.json   per-screen field models
 *   index/write-endpoints.json  payloads and id shapes
 *
 * Output: http/graph.json
 */
import fs from 'node:fs';
import path from 'node:path';

const KG = 'knowlegde_graph/blue-yonder-sce';
const FLOWS = path.join(KG, 'http/flows');
const EXCH = path.join(KG, 'http/exchanges');
const OUT = path.join(KG, 'http/graph.json');

const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const exists = (p) => fs.existsSync(p);

/*
 * Resource name from a URL fragment. The recorded forms are inconsistent because different
 * capture tools stored different slices: a full URL, "wm/addresses", or a bare "addresses".
 * Normalising in one place avoids the failure where every endpoint collapsed to the literal
 * "wm" and self-edges were then silently dropped, yielding zero dataflow edges.
 */
const resourceOf = (raw) => {
  const s0 = String(raw || '').split('?')[0];
  let s;
  const i = s0.indexOf('/wm/');
  if (i >= 0) s = s0.slice(i + 4);
  else if (s0.startsWith('wm/')) s = s0.slice(3);
  // Strict: only /wm/ paths name a WM resource. A permissive fallback turned MCS URLs
  // (/data/MCS/mcs/...) into a resource literally called "https:" - a node describing nothing.
  else return '';
  const name = s.split('/').filter(Boolean)[0] || '';
  return /^[A-Za-z][A-Za-z0-9_]*$/.test(name) ? name : '';
};

const nodes = new Map();   // id -> node
const edges = [];

const addNode = (id, type, props = {}) => {
  if (!nodes.has(id)) nodes.set(id, { id, type, ...props });
  else Object.assign(nodes.get(id), props);
  return nodes.get(id);
};
const addEdge = (from, to, type, props = {}) => {
  const key = `${from}|${type}|${to}|${props.field || ''}`;
  if (edges.some((e) => e.key === key)) return;
  edges.push({ key, from, to, type, ...props });
};

/* ---------- resources: operations and observed status codes ---------- */
if (exists(EXCH)) {
  for (const f of fs.readdirSync(EXCH).filter((x) => x.endsWith('.jsonl'))) {
    const resource = f.replace('.jsonl', '');
    const recs = fs.readFileSync(path.join(EXCH, f), 'utf8').split('\n').filter(Boolean).map(JSON.parse);
    const ops = {};
    let alive = true;
    for (const r of recs) {
      const m = r.request.method;
      const st = r.response?.status;
      const kind = r.response?.kind;
      ops[m] = ops[m] || { statuses: new Set(), cases: {} };
      ops[m].statuses.add(st);
      ops[m].cases[r.case] = `${st}${kind && kind !== 'OK' ? '/' + kind : ''}`;
      if (kind === 'ROUTE-MISSING') alive = false;
    }
    addNode(`resource:${resource}`, 'resource', {
      resource,
      exists: alive,
      operations: Object.fromEntries(Object.entries(ops).map(([m, v]) => [m, {
        statuses: [...v.statuses].sort(), cases: v.cases,
      }])),
      evidence: `http/exchanges/${f}`,
    });
  }
}

/* ---------- payloads, id shapes and gotchas from the ledger ---------- */
const ledgerPath = path.join(KG, 'index/write-endpoints.json');
if (exists(ledgerPath)) {
  for (const e of readJSON(ledgerPath)) {
    const n = addNode(`resource:${e.resource}`, 'resource', { resource: e.resource });
    n.verified_ops = n.verified_ops || {};
    n.verified_ops[e.method] = { verified: e.verified, pathPattern: e.pathPattern };
    if (e.payload) {
      /*
       * Payload templates were captured from real requests, so any foreign key in them is a REAL
       * id from capture time (e.g. addressId "A000365885"). Replayed verbatim that would attach
       * the new record to an unrelated existing row. Replace those with placeholders and record
       * which fields must be supplied from a prior step - the dataflow edges say where from.
       */
      n.payload = { ...e.payload };
    }
    if (e.id_shape) n.id_shape = e.id_shape;
    if (e.gotcha) n.gotcha = e.gotcha;
  }
}

/* ---------- screens: fields, and the resources they read and write ---------- */
const fmPath = path.join(KG, 'index/form-models.json');
if (exists(fmPath)) {
  for (const s of readJSON(fmPath)) {
    if (s.error) { addNode(`screen:${s.screen}`, 'screen', { screen: s.screen, route: s.route, form_model_error: s.error }); continue; }
    addNode(`screen:${s.screen}`, 'screen', {
      screen: s.screen, route: s.route,
      field_count: s.total,
      required_fields: (s.required || []).map((f) => ({ label: f.label, field: f.field, type: f.type, maxLength: f.maxLength })),
      evidence: 'index/form-models.json',
    });
  }
}

/*
 * Flow traces give the two most valuable edge types:
 *   screen -> resource   (which resource a phase actually reads or writes)
 *   resource -> resource (a value produced by one response consumed by a later request)
 */
const flowFiles = exists(FLOWS) ? fs.readdirSync(FLOWS).filter((f) => f.endsWith('.json')) : [];
for (const f of flowFiles) {
  const flow = readJSON(path.join(FLOWS, f));
  const screen = flow.screen || flow.spec || flow.target || f.replace('.json', '');
  const sid = `screen:${screen}`;
  addNode(sid, 'screen', { screen });

  const calls = flow.allCalls || flow.calls || [];
  for (const c of calls) {
    const method = c.method || c.request?.method;
    const rawUrl = c.url || c.request?.url || '';
    const resource = resourceOf(rawUrl);
    if (!resource) continue;
    const status = c.status ?? c.response?.status;
    const rid = `resource:${resource}`;
    addNode(rid, 'resource', { resource });
    addEdge(sid, rid, method === 'GET' ? 'reads' : 'writes', {
      method, status, phase: c.phase || null, evidence: `http/flows/${f}`,
    });
  }

  /*
   * Dataflow edges were computed at capture time by tools/cdp/trace.mjs, which matches a value
   * in a later request against values seen in earlier responses. That over-matches on AMBIENT
   * values: the client id "----" appears in almost every response on this system, so it produced
   * edges like packingConfigurations -> addresses that describe no real dependency.
   *
   * Distinguish by how widely the value occurs. A value carried by many responses was already in
   * the environment; a value appearing in exactly one response before being consumed is a real
   * server-assigned handoff (an addressId is the canonical case). Only the latter is treated as a
   * dependency strong enough to imply ordering.
   */
  const occurrences = new Map();
  for (const c of calls) {
    // Response bodies are stored differently by different capture tools: trace.mjs nests it as
    // response.body, the lifecycle runners store a plain string. Reading only one shape made
    // every value look unique and every edge look strong.
    const r = c.response;
    const blob = typeof r === 'string' ? r : (r && typeof r.body === 'string' ? r.body : JSON.stringify(r ?? ''));
    for (const e of (flow.edges || [])) {
      if (blob.includes(e.value)) occurrences.set(e.value, (occurrences.get(e.value) || 0) + 1);
    }
  }

  for (const e of (flow.edges || [])) {
    const fromRes = resourceOf(e.from.endpoint);
    const toRes = resourceOf(e.to.endpoint);
    if (!fromRes || !toRes || fromRes === toRes) continue;
    const seenIn = occurrences.get(e.value) || 1;
    const strong = seenIn <= 2;   // produced once (plus its own echo), then consumed
    addEdge(`resource:${fromRes}`, `resource:${toRes}`, 'dataflow', {
      field: `${e.from.field} => ${e.to.field}`,
      example_value: e.value,
      confidence: strong ? 'strong' : 'ambient',
      seen_in_responses: seenIn,
      meaning: strong
        ? `${toRes} consumes a value the ${fromRes} response assigned`
        : `value also present in ${seenIn} responses; likely ambient context rather than a handoff`,
      evidence: `http/flows/${f}`,
    });
    // Only a server-assigned handoff implies a real ordering constraint.
    if (strong) {
      addEdge(`resource:${toRes}`, `resource:${fromRes}`, 'requires', {
        meaning: `${fromRes} must exist before ${toRes} can be created`,
        via: e.from.field,
        evidence: `http/flows/${f}`,
      });
    }
  }
}

/*
 * Templatise foreign keys in captured payloads, using the DATAFLOW EDGES rather than a guess.
 *
 * Payloads were captured from real requests, so a foreign key still holds the real id from
 * capture time (suppliers carried addressId "A000365885"). Replayed verbatim, an executor would
 * attach its new record to an unrelated existing row. A name-based heuristic over-matched --
 * warehouseId "SG" is a constant, not a handoff -- so use the recorded evidence instead: a field
 * is a foreign key exactly when a strong dataflow edge lands on it.
 */
for (const n of nodes.values()) {
  if (n.type !== 'resource' || !n.payload) continue;
  const incoming = edges.filter((e) => e.type === 'dataflow' && e.confidence === 'strong' && e.to === n.id);
  const fks = new Set();
  for (const e of incoming) {
    const m = /=> body:([A-Za-z0-9_]+)/.exec(e.field || '');
    if (m) fks.add(m[1]);
  }
  const applied = [];
  for (const k of fks) {
    if (k in n.payload) {
      const src = incoming.find((e) => (e.field || '').includes(`body:${k}`));
      n.payload[k] = `<${k}: from ${src ? src.from.replace('resource:', '') : 'a prior step'}>`;
      applied.push(k);
    }
  }
  if (applied.length) n.payload_foreign_keys = applied;
}

/*
 * Tier 2/3 read-only traces.
 *
 * These operational areas were traced WITHOUT writing: their screens release work and move real
 * inventory, and several actions have no clean revert. Reads are still real structure - which
 * resources a screen depends on - so they become `reads` edges, and the buttons observed are
 * recorded as `available_actions` so a future writer knows what exists without anything having
 * been pressed.
 */
for (const f of flowFiles.filter((x) => x.startsWith('readonly-subroutes'))) {
  const doc = readJSON(path.join(FLOWS, f));
  for (const r of (doc.results || [])) {
    const sid = `screen:${r.area}/${r.label}`;
    addNode(sid, 'screen', {
      screen: r.label, area: r.area, route: r.route, tier: 'operational',
      read_only_trace: true,
      available_actions: r.state?.actions || [],
      grids: (r.state?.grids || []).length,
      evidence: `http/flows/${f}`,
    });
    for (const c of (r.calls || [])) {
      const resource = resourceOf(c.url);
      if (!resource || !/\/data\/WM\/wm\//.test(c.url)) continue;
      addNode(`resource:${resource}`, 'resource', { resource });
      addEdge(sid, `resource:${resource}`, c.method === 'GET' ? 'reads' : 'writes', {
        method: c.method, status: c.status, rowCount: c.rowCount ?? null,
        evidence: `http/flows/${f}`,
      });
    }
  }
}

/* ---------- cascades: ordered write sequences observed in a single UI action ---------- */
const cascades = [];
for (const f of flowFiles) {
  const flow = readJSON(path.join(FLOWS, f));
  const calls = (flow.allCalls || flow.calls || []);
  const writes = calls.filter((c) => (c.method || c.request?.method) !== 'GET');
  const created = writes.filter((c) => (c.phase === 'create' || !c.phase) && String(c.status ?? c.response?.status).startsWith('2'));
  if (created.length > 1) {
    cascades.push({
      flow: f,
      screen: flow.screen || flow.spec || flow.target,
      order: created.map((c) => {
        const u = c.url || c.request?.url || '';
        return `${c.method || c.request?.method} ${resourceOf(u)}`;
      }),
      note: 'Order is by request sequence, not response completion.',
      evidence: `http/flows/${f}`,
    });
  }
}

/* ---------- known hazards, carried into the graph so a traversal surfaces them ---------- */
const claimsPath = path.join(KG, 'http/claims.json');
const hazards = [];
if (exists(claimsPath)) {
  const claims = readJSON(claimsPath);
  for (const c of claims.claims || []) {
    if (/FALSIFIED|UNEXPLAINED/.test(c.verdict || '')) {
      hazards.push({ id: c.id, verdict: c.verdict, impact: c.impact || c.assessment || null,
        operational_rule: c.operational_rule || null, evidence: c.evidence });
    }
  }
}

const graph = {
  generated_by: 'tools/build-graph.mjs',
  generated_from: ['http/flows/*.json', 'http/exchanges/*.jsonl', 'index/form-models.json', 'index/write-endpoints.json', 'http/claims.json'],
  principle: 'Every edge is derived from a recorded exchange and carries its evidence file. Nothing here is inferred from naming or convention.',
  counts: {},
  nodes: [...nodes.values()],
  edges: edges.map(({ key, ...e }) => e),
  cascades,
  hazards,
};
graph.counts = {
  screens: graph.nodes.filter((n) => n.type === 'screen').length,
  resources: graph.nodes.filter((n) => n.type === 'resource').length,
  edges: graph.edges.length,
  dataflow_edges: graph.edges.filter((e) => e.type === 'dataflow').length,
  dataflow_strong: graph.edges.filter((e) => e.type === 'dataflow' && e.confidence === 'strong').length,
  requires_edges: graph.edges.filter((e) => e.type === 'requires').length,
  cascades: cascades.length,
  hazards: hazards.length,
};
fs.writeFileSync(OUT, JSON.stringify(graph, null, 2) + '\n');
console.log(JSON.stringify(graph.counts, null, 1));
console.log('\ndataflow edges:');
graph.edges.filter((e) => e.type === 'dataflow').forEach((e) => console.log(`  [${e.confidence.padEnd(7)}] ${e.from} -> ${e.to}  [${e.field}]`));
console.log('\nrequires (ordering constraints):');
graph.edges.filter((e) => e.type === 'requires').forEach((e) => console.log(`  ${e.from} requires ${e.to}  (via ${e.via})`));
console.log('\ncascades:');
cascades.forEach((c) => console.log(`  ${c.screen}: ${c.order.join('  ->  ')}`));
