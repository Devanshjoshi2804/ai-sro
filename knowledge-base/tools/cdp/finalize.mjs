import fs from 'node:fs';
const P = 'knowlegde_graph/blue-yonder-sce/index/write-endpoints.json';
const e = JSON.parse(fs.readFileSync(P, 'utf8'));
for (const x of e) {
  if (x.resource === 'carrierProNumbers' && x.method === 'POST') {
    x.payload = { addressId: '<existing addressId>', carrier: '<existing carrierCode>',
      poolPointAddressId: '<any new distinguishing string>', checkDigitMethod: '', format: '',
      numberLength: '10', nextValue: '', prefix: '', separator: '' };
    x.payload_source = 'Proven directly against the API (POST 201 -> GET -> PUT persisted -> DELETE -> RECORD-MISSING). NOT UI-captured: the Add form cannot be made valid.';
    x.gotcha = 'The Add form is unusable. Carrier is a carrierLookup and Carrier Facility Address a wmAddress, both with EMPTY stores; even loading the store and setting the model value directly leaves the field reporting "This field is required". Save then fires nothing at all - no error, no modal, no request. Automation must bypass this form and POST directly. resourceId is {addressId}*!{carrier}*!{poolPointAddressId}.';
    x.reverified_at = '2026-08-12';
  }
  if (x.resource === 'locations' && x.method === 'POST') {
    x.payload_source = 'NOT captured. Deliberately skipped: 25k+ real rows and a batch-create path, no provably isolated throwaway target.';
  }
}
fs.writeFileSync(P, JSON.stringify(e, null, 2) + '\n');
const posts = e.filter(x => x.method === 'POST');
const missing = posts.filter(x => !x.payload);
console.log('POST endpoints with executable payload:', posts.filter(x => x.payload).length, '/', posts.length);
console.log('without payload:', missing.map(x => `${x.resource} (${x.verified ? 'verified' : 'NOT verified'})`).join(', '));
