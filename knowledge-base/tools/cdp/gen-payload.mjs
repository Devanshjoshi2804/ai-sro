/*
 * gen-payload.mjs — turn a captured Add-form model into a candidate create payload.
 *
 * This is the step that makes the map executable. form-models-all.json holds, per creatable
 * screen, the real field model behind Add: JSON key, label, required flag, type, maxLength, and
 * the allowed values of small combos. From that we can propose a body without guessing at names —
 * which matters because the API's own errors cannot give them: a failed create returns a 422
 * naming the missing DB COLUMN (`lngdsc`), while the body must use a camelCase key
 * (`businessUnitDescription`) that is not derivable from it.
 *
 * What this deliberately does NOT do is claim the payload is correct. It produces a CANDIDATE.
 * Only an executed create -> read-back -> delete cycle proves a payload, and that proof is
 * recorded separately in http/exchanges.
 *
 *   node tools/cdp/gen-payload.mjs                 all screens
 *   node tools/cdp/gen-payload.mjs "Customer Types"
 */
import fs from 'node:fs';

const KG = 'knowlegde_graph/blue-yonder-sce';
const SRC = `${KG}/index/form-models-all.json`;
const OUT = `${KG}/index/create-candidates.json`;

const forms = JSON.parse(fs.readFileSync(SRC, 'utf8')).forms;

/* A short unique token that fits the tightest observed field limits. */
const token = (i, max) => {
  const t = 'ZV' + String(i).padStart(3, '0');
  return max && max < t.length ? t.slice(0, max) : t;
};

/*
 * Choose a value for one field.
 * Returns null when we cannot responsibly invent one - a combo whose options were not captured
 * is a foreign key into another resource, and inventing a value there produces a create that
 * either fails or, worse, links to the wrong record.
 */
function valueFor(field, idx) {
  const { type, maxLength, options } = field;
  if (options && options.length) return { value: options[0], source: 'first captured option' };

  switch (type) {
    case 'numberfield':
      return { value: 1, source: 'numeric default' };
    case 'checkbox':
    case 'checkboxfield':
    case 'radiogroup':
      return { value: false, source: 'boolean default' };
    case 'textfield':
    case 'textarea':
      return { value: token(idx, maxLength), source: 'generated token' };
    case 'combo':
    case 'combobox':
    case 'rpcombo':
      return { value: null, source: 'UNRESOLVED: combo with no captured options — needs a real value from its bound resource' };
    case 'wmAddress':
      return { value: null, source: 'UNRESOLVED: address composite — value is a full Address record, and creating one first orphans it if the parent create fails' };
    case 'carrierLookup':
      return { value: null, source: 'UNRESOLVED: lookup whose store is empty until searched; typed text never binds' };
    default:
      return { value: token(idx, maxLength), source: `fallback token for xtype ${type}` };
  }
}

const results = [];
const filter = process.argv[2];

for (const f of forms) {
  if (f.error || !f.fields) continue;
  if (filter && f.label !== filter) continue;

  const required = f.fields.filter((x) => x.required && x.field);
  const payload = {};
  const unresolved = [];
  const notes = [];

  required.forEach((fld, i) => {
    const v = valueFor(fld, i + 1);
    if (v.value === null) {
      unresolved.push({ field: fld.field, label: fld.label, type: fld.type, why: v.source });
    } else {
      payload[fld.field] = v.value;
      if (fld.maxLength && fld.maxLength <= 6) {
        notes.push(`${fld.field} maxLength ${fld.maxLength} — codes must stay short`);
      }
    }
  });

  results.push({
    screen: f.label,
    area: f.area,
    tier: f.tier,
    hash: f.hash,
    required_count: required.length,
    payload,
    unresolved,
    // A payload is only auto-runnable when every required field could be filled responsibly.
    ready: unresolved.length === 0 && required.length > 0,
    notes,
  });
}

fs.writeFileSync(OUT, JSON.stringify({
  generated_by: 'tools/cdp/gen-payload.mjs',
  warning: 'These are CANDIDATE payloads derived from form models. None is verified. A payload is proven only by an executed create -> read-back -> delete cycle recorded in http/exchanges.',
  candidates: results,
}, null, 2) + '\n');

const ready = results.filter((r) => r.ready);
const blocked = results.filter((r) => !r.ready);
console.log(JSON.stringify({
  screens: results.length,
  ready_to_attempt: ready.length,
  blocked_on_unresolved_fields: blocked.length,
  blockers: blocked.flatMap((b) => b.unresolved.map((u) => u.type))
    .reduce((a, t) => (a[t] = (a[t] || 0) + 1, a), {}),
}, null, 1));
console.log('\nready:', ready.map((r) => r.screen).slice(0, 25).join(', '));
