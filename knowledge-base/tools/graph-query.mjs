/*
 * graph-query.mjs — answer the questions an executor actually asks of the graph.
 *
 *   node tools/graph-query.mjs plan suppliers      what must exist first, and what to send
 *   node tools/graph-query.mjs resource clients    operations, status codes, payload, hazards
 *   node tools/graph-query.mjs screen printers     required fields, what it reads and writes
 *   node tools/graph-query.mjs hazards             everything known to be unsafe or wrong
 *
 * Answers are assembled from http/graph.json only, and every fact carries the evidence file it
 * came from, so a caller can check any statement rather than trusting it.
 */
import fs from 'node:fs';

const G = JSON.parse(fs.readFileSync('knowlegde_graph/blue-yonder-sce/http/graph.json', 'utf8'));
const node = (id) => G.nodes.find((n) => n.id === id);
const res = (name) => node(`resource:${name}`);
const out = (...a) => console.log(...a);

/* Ordering constraints, resolved transitively: what must exist before this can be created. */
function plan(name) {
  const target = res(name);
  if (!target) return out(`unknown resource: ${name}`);
  const order = [];
  const seen = new Set();
  (function walk(rname) {
    if (seen.has(rname)) return;
    seen.add(rname);
    for (const e of G.edges.filter((x) => x.type === 'requires' && x.from === `resource:${rname}`)) {
      walk(e.to.replace('resource:', ''));
    }
    order.push(rname);
  })(name);

  out(`\nCREATE PLAN: ${name}\n`);
  out('Order:');
  order.forEach((r, i) => {
    const n = res(r);
    out(`  ${i + 1}. POST /wm/${r}` + (n?.id_shape ? `   (id: ${n.id_shape})` : ''));
  });

  out('\nHandoffs between steps:');
  const flows = G.edges.filter((e) => e.type === 'dataflow' && e.confidence === 'strong'
    && order.includes(e.from.replace('resource:', '')) && order.includes(e.to.replace('resource:', '')));
  if (!flows.length) out('  (none recorded)');
  flows.forEach((e) => out(`  ${e.from.replace('resource:', '')} -> ${e.to.replace('resource:', '')}: ${e.field}   [${e.evidence}]`));

  for (const r of order) {
    const n = res(r);
    if (!n) continue;
    out(`\n--- ${r} ---`);
    if (n.payload) out('payload: ' + JSON.stringify(n.payload));
    if (n.gotcha) out('GOTCHA: ' + n.gotcha);
    const dup = n.operations?.POST?.cases?.['create-duplicate'];
    if (dup) out(`duplicate create returns: ${dup}`);
  }

  const hz = G.hazards.filter((h) => order.some((r) => (h.id || '').includes(r)));
  if (hz.length) {
    out('\nHAZARDS on this path:');
    hz.forEach((h) => out(`  [${h.verdict}] ${h.id}\n     ${h.operational_rule || h.impact || ''}`));
  }
}

function resource(name) {
  const n = res(name);
  if (!n) return out(`unknown resource: ${name}`);
  out(`\nRESOURCE: ${name}`);
  out(`exists: ${n.exists !== false}` + (n.exists === false ? '   <-- ROUTE DOES NOT EXIST' : ''));
  if (n.id_shape) out(`id shape: ${n.id_shape}`);
  if (n.payload) out(`payload: ${JSON.stringify(n.payload)}`);
  if (n.gotcha) out(`GOTCHA: ${n.gotcha}`);
  if (n.operations) {
    out('\nobserved behaviour:');
    for (const [m, v] of Object.entries(n.operations)) {
      out(`  ${m}: statuses ${v.statuses.join(', ')}`);
      for (const [c, s] of Object.entries(v.cases)) out(`     ${c.padEnd(20)} ${s}`);
    }
  }
  const needs = G.edges.filter((e) => e.type === 'requires' && e.from === n.id);
  if (needs.length) out('\nrequires first: ' + needs.map((e) => e.to.replace('resource:', '')).join(', '));
  const writers = G.edges.filter((e) => e.type === 'writes' && e.to === n.id).map((e) => e.from.replace('screen:', ''));
  if (writers.length) out('written by screens: ' + [...new Set(writers)].join(', '));
  if (n.evidence) out(`\nevidence: ${n.evidence}`);
}

function screen(name) {
  const n = node(`screen:${name}`);
  if (!n) return out(`unknown screen: ${name}`);
  out(`\nSCREEN: ${name}`);
  if (n.route) out(`route: ${n.route}`);
  if (n.form_model_error) out(`form model NOT captured: ${n.form_model_error}`);
  if (n.required_fields?.length) {
    out('\nrequired fields (label -> JSON field):');
    n.required_fields.forEach((f) => out(`  ${String(f.label || '(none)').padEnd(34)} -> ${String(f.field).padEnd(24)} ${f.type}${f.maxLength ? ' max' + f.maxLength : ''}`));
  }
  const w = G.edges.filter((e) => e.type === 'writes' && e.from === n.id);
  const r = G.edges.filter((e) => e.type === 'reads' && e.from === n.id);
  if (w.length) {
    out('\nwrites:');
    w.forEach((e) => out(`  ${e.phase || '-'}: ${e.method} /wm/${e.to.replace('resource:', '')} -> ${e.status}`));
  }
  if (r.length) out('\nreads: ' + [...new Set(r.map((e) => e.to.replace('resource:', '')))].join(', '));
}

function hazards() {
  out('\nHAZARDS\n');
  G.hazards.forEach((h) => {
    out(`[${h.verdict}] ${h.id}`);
    if (h.operational_rule) out(`   RULE: ${h.operational_rule}`);
    else if (h.impact) out(`   ${h.impact}`);
    out(`   evidence: ${h.evidence}\n`);
  });
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === 'plan') plan(arg);
else if (cmd === 'resource') resource(arg);
else if (cmd === 'screen') screen(arg);
else if (cmd === 'hazards') hazards();
else {
  out('usage: plan <resource> | resource <name> | screen <name> | hazards');
  out(`\ngraph: ${G.counts.screens} screens, ${G.counts.resources} resources, ${G.counts.edges} edges`);
  out(`strong dataflow: ${G.counts.dataflow_strong}, ordering constraints: ${G.counts.requires_edges}, cascades: ${G.counts.cascades}, hazards: ${G.counts.hazards}`);
}
