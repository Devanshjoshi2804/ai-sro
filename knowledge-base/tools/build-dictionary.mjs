/*
 * build-dictionary.mjs — join the scraped help corpus to the captured form models.
 *
 * WHY THIS MATTERS
 * The two halves of this knowledge base were built independently and never connected:
 *
 *   captured (from the live app)  JSON key, type, required, maxLength   — the MECHANICS
 *   scraped  (from the help site) label, business description, procedure — the SEMANTICS
 *
 * Neither is sufficient alone. The capture knows `supplierNumber` is a required 32-char textfield
 * but not what a supplier IS. The help corpus explains suppliers thoroughly but never mentions
 * `supplierNumber`, because user documentation speaks in labels, not payload keys.
 *
 * The join key is the visible label, and it works: 96% of captured fields carrying a label match
 * a documented field. The result is the layer an agent actually needs — for any payload key, what
 * it means, what it is for, and which screens and procedures use it.
 *
 * Output: index/field-dictionary.json
 */
import fs from 'node:fs';

const KG = 'knowlegde_graph/blue-yonder-sce';
const help = JSON.parse(fs.readFileSync(`${KG}/index/fields.json`, 'utf8'));
const forms = JSON.parse(fs.readFileSync(`${KG}/index/form-models-all.json`, 'utf8')).forms.filter((f) => !f.error);
const appMap = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const procedures = JSON.parse(fs.readFileSync(`${KG}/index/procedures.json`, 'utf8'));

/*
 * Some grid/form labels arrive as rendered HTML with a stacked header and its help text inline.
 * Stripping tags recovers the real label and lifts the match rate; without it those fields look
 * undocumented when they are simply wrapped.
 */
const cleanLabel = (s) => String(s || '')
  .replace(/<[^>]*>/g, ' ')
  .replace(/&nbsp;/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const norm = (s) => cleanLabel(s).toLowerCase().replace(/[^a-z0-9]/g, '');

/* Index help definitions by normalised label. Keep the first, richest definition per label. */
const helpByLabel = new Map();
for (const h of help) {
  const k = norm(h.field);
  if (!k) continue;
  const prev = helpByLabel.get(k);
  if (!prev || (h.description || '').length > (prev.description || '').length) helpByLabel.set(k, h);
}

/* Which procedures mention a given label, so a key can be traced to the task that uses it. */
const procByLabel = new Map();
for (const p of procedures) {
  const blob = JSON.stringify(p.steps || []).toLowerCase();
  for (const [k, h] of helpByLabel) {
    if (k.length < 5) continue;                 // short tokens produce noise
    if (blob.includes(cleanLabel(h.field).toLowerCase())) {
      if (!procByLabel.has(k)) procByLabel.set(k, []);
      const list = procByLabel.get(k);
      if (list.length < 4 && !list.includes(p.name)) list.push(p.name);
    }
  }
}

/* Screens that read each resource, so a field can be tied back to where it is used. */
const screensByLabel = new Map();
for (const f of forms) {
  for (const fl of f.fields || []) {
    const k = norm(fl.label);
    if (!k) continue;
    if (!screensByLabel.has(k)) screensByLabel.set(k, new Set());
    screensByLabel.get(k).add(f.label);
  }
}

const entries = new Map();   // json key -> entry
let withLabel = 0, matched = 0;

for (const f of forms) {
  for (const fl of f.fields || []) {
    if (!fl.field) continue;
    const label = cleanLabel(fl.label);
    if (label) withLabel++;
    const h = label ? helpByLabel.get(norm(label)) : null;
    if (h) matched++;

    const existing = entries.get(fl.field);
    const screens = [...(screensByLabel.get(norm(label)) || [])].slice(0, 8);
    const entry = existing || {
      key: fl.field,
      labels: [],
      type: fl.type,
      required_on: [],
      maxLength: fl.maxLength,
      documented: !!h,
      description: h ? h.description : null,
      help_page: h ? h.page_url : null,
      help_section: h ? h.table_caption : null,
      toc_path: h ? h.toc_path : null,
      procedures: h ? (procByLabel.get(norm(label)) || []) : [],
      screens,
    };
    if (label && !entry.labels.includes(label)) entry.labels.push(label);
    if (fl.required && !entry.required_on.includes(f.label)) entry.required_on.push(f.label);
    if (!entry.documented && h) {
      Object.assign(entry, { documented: true, description: h.description, help_page: h.page_url, help_section: h.table_caption, toc_path: h.toc_path });
    }
    entries.set(fl.field, entry);
  }
}

const list = [...entries.values()].sort((a, b) => a.key.localeCompare(b.key));
fs.writeFileSync(`${KG}/index/field-dictionary.json`, JSON.stringify({
  generated_by: 'tools/build-dictionary.mjs',
  what_this_is: 'Payload key -> visible label -> business meaning, joined from the live-app capture and the scraped help corpus. The capture supplies the key and constraints; the help corpus supplies what the field means and which procedures use it.',
  join_key: 'visible field label, normalised (case and punctuation removed, HTML stripped)',
  totals: { keys: list.length, documented: list.filter((e) => e.documented).length },
  fields: list,
}, null, 2) + '\n');

console.log(JSON.stringify({
  distinct_payload_keys: list.length,
  documented: list.filter((e) => e.documented).length,
  undocumented: list.filter((e) => !e.documented).length,
  label_match_rate: `${Math.round(matched / withLabel * 100)}%`,
  help_definitions_available: helpByLabel.size,
  keys_required_somewhere: list.filter((e) => e.required_on.length).length,
}, null, 1));
console.log('\nsample:');
for (const e of list.filter((x) => x.documented && x.required_on.length).slice(0, 4)) {
  console.log(`  ${e.key}  "${e.labels[0]}"  [required on: ${e.required_on.join(', ')}]`);
  console.log(`     ${String(e.description).slice(0, 150)}`);
}
