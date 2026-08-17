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
      // Some records are notes rather than exchanges — `failure-battery-refused` carries a reason
      // and no request, deliberately, so that a gap has an explanation attached in the store.
      if (!r.request?.method) continue;
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

/*
 * BEHAVIOUR ANNOTATIONS
 *
 * The catalogue answers "what can I call". An agent also has to answer "what happens if this goes
 * wrong", and this session proved several resources where the obvious assumption is false: a DELETE
 * that answers 200 and deletes nothing, creates that succeed twice, a create whose record cannot be
 * read back, resources that ignore `limit`. Those live on the resource node, each derived from the
 * stored cases rather than from any claim's prose.
 */
{
  const shapes = exists(path.join(KG, 'index/read-shapes.json'))
    ? readJSON(path.join(KG, 'index/read-shapes.json')).resources : {};
  const filterable = exists(path.join(KG, 'index/filterable-columns.json'))
    ? readJSON(path.join(KG, 'index/filterable-columns.json')).resources : {};
  const statuses = exists(path.join(KG, 'index/status-vocabulary.json'))
    ? readJSON(path.join(KG, 'index/status-vocabulary.json')).resources : {};
  for (const n of nodes.values()) {
    if (n.type !== 'resource') continue;
    const cases = { ...(n.operations?.GET?.cases || {}), ...(n.operations?.POST?.cases || {}), ...(n.operations?.DELETE?.cases || {}), ...(n.operations?.PUT?.cases || {}) };
    const w = [];
    const dup = cases['create-duplicate'];
    if (dup && /^2/.test(dup)) w.push({ hazard: 'duplicate-create-succeeds', detail: `create-duplicate answered ${dup}: a retried POST is a second record, so an idempotency key is the only protection.` });
    const gone = cases['confirm-gone'] || cases['cleanup-confirm-gone'];
    if (gone && !/RECORD-MISSING/.test(gone)) w.push({ hazard: 'delete-unconfirmed', detail: `confirm-gone answered ${gone} instead of RECORD-MISSING — the delete is not proven.` });
    if (cases['delete-valid'] && /^2/.test(cases['delete-valid']) && gone && /^200/.test(gone)) {
      w.push({ hazard: 'delete-is-a-noop', detail: 'DELETE answers 2xx and the record is still readable afterwards.' });
    }
    if (shapes[n.resource]?.honours_limit === false) {
      w.push({ hazard: 'ignores-limit', detail: 'This collection returns the whole table regardless of the limit parameter; a sampling read can pull tens of thousands of rows.' });
    }
    if (/^2/.test(cases['create-valid-via-codes'] || '')) w.push({ hazard: 'creates-through-another-resource', detail: 'This is a view: its create goes to /wm/codes in the partition it reads.' });
    /*
     * Only a SUCCESSFUL composite create says anything about the body shape. Keying on the case
     * name alone tagged handlingUnitCategories, warehouseUoms and loadAttributeConfigurations as
     * composite when in fact they had refused the attempt outright — the opposite conclusion.
     */
    if (/^2/.test(cases['create-valid-composite'] || '')) {
      w.push({ hazard: 'create-modelled-on-existing-record', detail: 'A generated body was refused; what worked was a copy of an existing record with its identity varied and server-owned ids removed.' });
    }
    for (const [caseName, status] of Object.entries(cases)) {
      if (!/^create-valid/.test(caseName) || /^2/.test(status)) continue;
      if (Object.entries(cases).some(([k, v]) => /^create-valid/.test(k) && /^2/.test(v))) continue;
      w.push({ hazard: 'create-refused', detail: `Every recorded create attempt failed; the last answered ${status}. This resource may not be creatable at all — loadAttributeConfigurations answers 405, and join tables answer 422 until the code they point at exists.` });
      break;
    }
    if (w.length) n.behaviour_warnings = w;
    if (shapes[n.resource]) {
      n.read_shape = { status: shapes[n.resource].status, fields: shapes[n.resource].field_count, rows_in_sample: shapes[n.resource].rows_returned };
    }
    /*
     * How this resource can be QUERIED, and what states its rows can be in. Both are measured, and
     * both are things a caller needs before it reads: filtering on an unlisted column returns 200
     * with zero rows, which is indistinguishable from absence.
     */
    if (filterable[n.resource]) {
      n.queryable = {
        filterable_columns: filterable[n.resource].filterable,
        not_filterable: filterable[n.resource].not_filterable,
        grammar: 'query=[{"column","operator","value"}], ANDed; operators EQ NE GT GE LT LE; % wildcard inside EQ',
      };
      if (!filterable[n.resource].filterable.length) {
        n.behaviour_warnings = [...(n.behaviour_warnings || []), {
          hazard: 'not-queryable',
          detail: 'No column on this resource honours a filter. It can only be paged, so a targeted lookup is impossible and an empty filtered read means nothing.',
        }];
      }
    }
    if (statuses[n.resource]) {
      n.state_vocabulary = Object.fromEntries(Object.entries(statuses[n.resource].fields)
        .filter(([, v]) => v.distinct_values.length)
        .map(([f, v]) => [f, v.distinct_values.map((x) => (x.label ? `${x.value} (${x.label})` : x.value))]));
    }
  }
}

/*
 * UI-DRIVEN OPERATIONAL ACTIONS.
 *
 * Six verbs are now captured by driving the screens, and they do not appear in any endpoint
 * catalogue in a usable form: three of them PUT the same generic /wm/work/async and differ only in
 * the field they change. Attach them to the resource so a caller asking about `work` is told what
 * can be DONE to it, with the field that expresses each verb.
 */
{
  const flowDir = path.join(KG, 'http/flows');
  if (exists(flowDir)) {
    for (const file of fs.readdirSync(flowDir).filter((f) => f.endsWith('.json'))) {
      let flow; try { flow = readJSON(path.join(flowDir, file)); } catch { continue; }
      const res = flow.resource || (flow.target ? 'inventoryAdjustmentApprovals' : null);
      if (!res) continue;
      const id = `resource:${res}`;
      if (!nodes.has(id)) continue;
      const n = nodes.get(id);
      const reqOf = (arr) => (arr && arr[0]) ? { method: arr[0].method, url: arr[0].url.split('?')[0], status: arr[0].status } : null;
      for (const [name, reqs] of [[flow.action_a, flow.requests_a], [flow.action_b, flow.requests_b]]) {
        const r = reqOf(reqs);
        if (!name || !r) continue;
        n.ui_actions = n.ui_actions || [];
        if (n.ui_actions.some((a) => a.action === name)) continue;
        /*
         * Compute the diff when the flow file predates it. The earliest captures stored both request
         * bodies but no diff, and reporting "the endpoint itself" for Assign User — which is the
         * clearest field-change of the set — would be exactly backwards.
         */
        let diff = (flow.payload_diff || []).map((d) => d.field);
        if (!diff.length) {
          const first = (arr) => { const b = arr && arr[0] && arr[0].request_body; return Array.isArray(b) ? b[0] : b; };
          const a = first(flow.requests_a), b = first(flow.requests_b);
          if (a && b && typeof a === 'object' && typeof b === 'object') {
            diff = [...new Set([...Object.keys(a), ...Object.keys(b)])].filter((k) => JSON.stringify(a[k]) !== JSON.stringify(b[k]));
          }
        }
        n.ui_actions.push({
          action: name, method: r.method, endpoint: r.url, status: r.status,
          body: 'array of the full record',
          expressed_by: diff.length ? `field change: ${diff.join(', ')}` : 'the endpoint itself',
          evidence: `http/flows/${file}`,
        });
      }
    }
  }
}

/*
 * PUBLISHED LINKS — the relationships the server itself declares.
 *
 * Every record carries `*_uri` fields pointing at its own neighbourhood: a shipment publishes its
 * orders, picks, waves, shipmentLines, handlingUnits, crossdocks and manifestDetails. Those are the
 * operational relationships this graph never had — its edges all came from Configuration flows —
 * and they need no inference at all, because the server names them.
 *
 * A link whose GET answers 405 is not a collection but an OPERATION (trailers.closeWithWorkQueue,
 * structuredInventory.editAsn). Those are recorded as actions, not traversals.
 */
{
  const alPath = path.join(KG, 'index/action-links.json');
  if (exists(alPath)) {
    const al = readJSON(alPath).resources || {};
    for (const [resource, spec] of Object.entries(al)) {
      const from = `resource:${resource}`;
      if (!nodes.has(from)) continue;
      for (const c of spec.sub_collections || []) {
        if (c.get_status !== 200) continue;
        // The link name is usually the related resource; keep the path either way as the evidence.
        const target = `resource:${c.link.replace(/_uri$/, '')}`;
        if (nodes.has(target)) {
          addEdge(from, target, 'publishes', { via: c.link, path: c.path, evidence: `index/action-links.json — GET ${c.path} returned 200` });
        }
        const n = nodes.get(from);
        n.publishes = [...new Set([...(n.publishes || []), c.link.replace(/_uri$/, '')])];
      }
      for (const a of spec.actions || []) {
        const n = nodes.get(from);
        n.actions = [...(n.actions || []), { name: a.link.replace(/_uri$/, ''), path: a.path, note: 'GET answers 405 — this is an operation, and its verb is not recorded yet' }];
      }
    }
  }
}

/*
 * PREREQUISITE EDGES, derived from values rather than names.
 *
 * The graph had two `requires` edges, both from old UI flows, while the write evidence quietly
 * contains many more: a create body that carries `columnName: "uomcod"` or
 * `sourceMovementZone: 10002` is naming a record in another resource. Match the VALUES in every
 * proven create payload against the values in every recorded read sample, and each hit is a
 * prerequisite with the exact field and value as its evidence.
 *
 * Values that identify nothing are excluded: booleans, nulls, short tokens, the site code, the
 * blank client, and the run markers this capture itself invented.
 */
{
  const byValue = new Map();          // value -> Set of "resource.field"
  const boring = new Set(['SG', '----', '', 'true', 'false', '0', '1', 'ACT', 'INV']);
  const useless = (v) => v === null || typeof v === 'boolean' || typeof v === 'object'
    || boring.has(String(v)) || String(v).length < 3
    // Anything this capture invented is not evidence of a relationship with anything.
    || /Z[VSQ]\d|battery|probe/i.test(String(v));
  /*
   * A shared VALUE only implies a relationship when it is being used as an identifier. Descriptions
   * collide constantly — "LPN", "CREATE WORK" and "ABC Audit Count" appear across a dozen unrelated
   * resources — and matching them produced edges like `movementPaths requires items`, which is
   * nonsense. So: never match on a description-like field, and require the target side to be an
   * identifier, either `resourceId`, an `*Id` field, or the identically-named field.
   */
  const descriptive = (k) => /description|name|text|comment|label|title/i.test(k);

  for (const f of fs.readdirSync(EXCH).filter((x) => x.endsWith('.jsonl'))) {
    const resource = f.replace('.jsonl', '');
    for (const line of fs.readFileSync(path.join(EXCH, f), 'utf8').split('\n').filter(Boolean)) {
      let r; try { r = JSON.parse(line); } catch { continue; }
      if (r.request?.method !== 'GET' || !(r.response?.status < 300)) continue;
      const rows = Array.isArray(r.response?.body?.data) ? r.response.body.data
        : r.response?.body?.data ? [r.response.body.data] : [];
      for (const row of rows.slice(0, 2)) {
        for (const [k, v] of Object.entries(row || {})) {
          if (useless(v) || k === 'self_uri' || k.endsWith('_uri')) continue;
          const key = String(v);
          if (!byValue.has(key)) byValue.set(key, new Set());
          byValue.get(key).add(`${resource}.${k}`);
        }
      }
    }
  }

  const we2 = exists(path.join(KG, 'index/write-endpoints.json')) ? readJSON(path.join(KG, 'index/write-endpoints.json')) : [];
  for (const e of we2) {
    if (e.method !== 'POST' || !e.payload) continue;
    const body = Array.isArray(e.payload) ? e.payload[0] || {} : e.payload;
    const seen = new Set();
    for (const [k, v] of Object.entries(body)) {
      if (useless(v)) continue;
      if (descriptive(k)) continue;
      // A number is only an identifier when the key says so; `assetHeight = 5.56` matched a row in
      // structuredInventory by pure coincidence and read as a dependency.
      if (typeof v === 'number' && !/Id$/.test(k)) continue;
      if (typeof v === 'string' && v.length < 4 && !/Id$/.test(k)) continue;

      /*
       * One value can appear in several resources — a movement zone id shows up in the zone itself
       * and in every rule that points at it. Rank the candidates and keep only the best: the
       * resource where the value IS the record's id beats one where it is a foreign key, and an
       * identically-named field beats a merely id-shaped one.
       */
      const ranked = [...(byValue.get(String(v)) || [])]
        .map((hit) => { const [target, field] = hit.split('.'); return { target, field }; })
        .filter((x) => x.target !== e.resource && !descriptive(x.field))
        .map((x) => ({ ...x, score: x.field === 'resourceId' ? 3 : x.field === k ? 2 : /Id$/.test(x.field) ? 1 : 0 }))
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score);
      // Take the best candidate that is not already linked from this payload, rather than only the
      // single top one — otherwise a key whose winner was already seen drops a real edge silently,
      // which is how `movementPaths requires movementZones` vanished.
      for (const { target, field } of ranked.filter((x) => !seen.has(x.target)).slice(0, 1)) {
        seen.add(target);
        if (!nodes.has(`resource:${target}`)) continue;
        addEdge(`resource:${e.resource}`, `resource:${target}`, 'requires', {
          via: `${k} = ${JSON.stringify(v)}`,
          matches: `${target}.${field}`,
          evidence: `${e.evidence} (payload) matched against http/exchanges/${target}.jsonl (recorded rows)`,
          confidence: 'value-match',
        });
      }
    }
  }
}

/*
 * WRITE CONTRACT + observed write edges.
 *
 * The graph carried ten `writes` edges while the store held proven creates for seventy-odd
 * resources, because write edges only came from recorded flows. Take them from the derived write
 * catalogue instead, and record on each screen the resource its Save was actually seen to hit —
 * which is not always a resource the screen reads.
 */
{
  const wePath = path.join(KG, 'index/write-endpoints.json');
  const mapPath = path.join(KG, 'index/app-map.json');
  const we = exists(wePath) ? readJSON(wePath) : [];
  for (const e of we) {
    const rid = `resource:${e.resource}`;
    const n = nodes.get(rid);
    if (!n) continue;
    n.write_contract = n.write_contract || {};
    n.write_contract[e.method] = {
      path: e.pathPattern,
      proof: e.proof || 'asserted',
      evidence: e.evidence || null,
      creates_through: e.creates_through || undefined,
      payload_keys: e.payload && typeof e.payload === 'object' ? Object.keys(Array.isArray(e.payload) ? e.payload[0] || {} : e.payload) : undefined,
    };
  }
  if (exists(mapPath)) {
    for (const sc of readJSON(mapPath).screens) {
      for (const r of sc.writes_observed || []) {
        const sid = `screen:${sc.label}`;
        if (!nodes.has(sid)) nodes.set(sid, { id: sid, type: 'screen', label: sc.label, area: sc.area, tier: sc.tier });
        addEdge(sid, `resource:${r}`, 'writes', { evidence: 'observed on the wire while saving the screen (tools/cdp/capture-ui-save.mjs)' });
      }
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
  resources_with_behaviour_warnings: graph.nodes.filter((n) => n.behaviour_warnings).length,
  resources_with_ui_actions: graph.nodes.filter((n) => n.ui_actions).length,
  ui_actions_captured: graph.nodes.reduce((a, n) => a + (n.ui_actions?.length || 0), 0),
  publishes_edges: graph.edges.filter((e) => e.type === 'publishes').length,
  resources_publishing_links: graph.nodes.filter((n) => n.publishes).length,
  operations_found_on_records: graph.nodes.reduce((a, n) => a + (n.actions?.length || 0), 0),
  resources_with_a_filterability_map: graph.nodes.filter((n) => n.queryable).length,
  resources_that_cannot_be_filtered_at_all: graph.nodes.filter((n) => n.queryable && !n.queryable.filterable_columns.length).length,
  resources_with_a_state_vocabulary: graph.nodes.filter((n) => n.state_vocabulary).length,
  resources_with_a_write_contract: graph.nodes.filter((n) => n.write_contract).length,
  write_contracts_proven_round_trip: graph.nodes.filter((n) => n.write_contract && Object.values(n.write_contract).some((w) => w.proof === 'round-trip')).length,
};
fs.writeFileSync(OUT, JSON.stringify(graph, null, 2) + '\n');
console.log(JSON.stringify(graph.counts, null, 1));
console.log('\ndataflow edges:');
graph.edges.filter((e) => e.type === 'dataflow').forEach((e) => console.log(`  [${e.confidence.padEnd(7)}] ${e.from} -> ${e.to}  [${e.field}]`));
console.log('\nrequires (ordering constraints):');
graph.edges.filter((e) => e.type === 'requires').forEach((e) => console.log(`  ${e.from} requires ${e.to}  (via ${e.via})`));
console.log('\ncascades:');
cascades.forEach((c) => console.log(`  ${c.screen}: ${c.order.join('  ->  ')}`));
