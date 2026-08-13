/*
 * patch-ledger.mjs — write the UI-captured payloads back into write-endpoints.json.
 *
 * The ledger previously recorded create bodies only as English prose inside `notes`, which is
 * why none of these endpoints were reproducible. Each entry below carries the body the app
 * itself sent, captured by tools/cdp/capture.mjs, plus the constraints that were discovered
 * only by driving the real form.
 */
import fs from 'node:fs';

const P = 'knowlegde_graph/blue-yonder-sce/index/write-endpoints.json';
const D = '2026-08-12';
const entries = JSON.parse(fs.readFileSync(P, 'utf8'));

const captured = {
  customerTypes: {
    payload: {
      customerType: '<=4 chars>', longDescription: '<text>', shotDescription: '',
      crossDockFlag: -1, bulkPickingFlag: false, outboundDateWindowUnit: 'MIN',
    },
    id_shape: 'bare code',
    gotcha: [
      'Description field is longDescription, NOT description.',
      'The API also ships a typo: shotDescription (sic) is the short-description key.',
      'customerType maps to column csttyp and truncates at 4 chars; longer values fail 422 with SQL -2628.',
      'Payload captured from the real UI Add form. It is NOT derivable from the API 422s.',
    ].join(' '),
  },
  equipmentTypes: {
    payload: {
      vehicleTypeId: '<code>', longDescription: '<text>', voiceCode: '<unique number>',
      vehicleLimit: '1', location: 0, captureEquipment: false, useWorkAreaMove: false,
    },
    id_shape: 'bare code',
    gotcha: [
      'FOUR required fields, not two: vehicleTypeId, longDescription, voiceCode, vehicleLimit.',
      'voiceCode is NUMERIC, truncates to 2 chars, and must be UNIQUE across all equipment types',
      '- the form rejects a duplicate with "The voice code already existed", a second uniqueness',
      'constraint beyond the primary key. 77 types exist here; lowest free voiceCode was 11.',
    ].join(' '),
  },
  levelTypes: {
    payload: {
      warehouseId: 'SG', levelTypeId: '', levelTypeName: '<name>', levelTypeDescription: '<text>',
      totalLevelUnits: 1, horizontalAlignmentFlag: false, verticalAlignmentFlag: false,
      displayPendingIndicatorFlag: false, maxWeight: 0, location: '', usedFlag: false,
      self_uri: '', maxWeightValidationFlag: false,
    },
    id_shape: '{zero-padded-numeric}*!{warehouseId}, server-assigned, e.g. 000000000000025*!SG',
    gotcha: [
      'Collection is empty in this environment, so field names cannot be sampled from an existing',
      'record - driving the UI was the ONLY way to obtain this payload.',
      'The form label is "Name" (-> levelTypeName), not "Level Type".',
      'totalLevelUnits is required and loses its displayed default when the form re-renders.',
    ].join(' '),
  },
};

const method = 'tools/cdp/capture.mjs (payload captured from the real UI Add form over CDP) '
  + '+ tools/cdp/api.mjs lifecycle: GET -> PUT (assert persisted) -> DELETE -> GET (assert RECORD-MISSING).';

let annotated = 0;
for (const entry of entries) {
  const c = captured[entry.resource];
  if (!c) continue;
  entry.reverified_at = D;
  entry.reverify_method = method;
  if (entry.method === 'POST') entry.payload = c.payload;
  entry.id_shape = c.id_shape;
  entry.gotcha = c.gotcha;
  annotated++;
}

fs.writeFileSync(P, JSON.stringify(entries, null, 2) + '\n');
const posts = entries.filter((x) => x.method === 'POST');
console.log('annotated entries:', annotated);
console.log('POST endpoints with an executable payload:', posts.filter((x) => x.payload).length, '/', posts.length);
console.log('still prose-only:', posts.filter((x) => !x.payload).map((x) => x.resource).join(', '));
