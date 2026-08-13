/* Isolate why a voice-device create 404s: identical body shape, different code length. */
import { connect, probe, summarize } from './http-record.mjs';
import fs from 'node:fs';
const ok = JSON.parse(fs.readFileSync('knowlegde_graph/blue-yonder-sce/index/captures/voiceDevices.json','utf8'));
const base = JSON.parse(ok.requests.find(r=>r.method==='POST').body);
const { browser, page } = await connect();
const results = [];
for (const code of ['ZVA1','ZVA12','ZVA123','ZVA1234']) {
  const body = { ...base, deviceCode: code, deviceName: 'ZV probe', voiceTerminalId: code };
  const r = await probe(page, { resource:'devices', caseName:`voice-create-len${code.length}`, method:'POST', urlPath:'/wm/devices', body,
    notes:'Isolating the voice-device 404: same body shape, varying deviceCode length.' });
  results.push(`${code} (len ${code.length}) -> ${r.response.status} ${r.response.kind}`);
  if (r.response.status === 201) {
    const id = r.response.body?.data?.resourceId;
    if (id) await probe(page, { resource:'devices', caseName:'voice-cleanup', method:'DELETE', urlPath:`/wm/devices/${encodeURIComponent(id)}` });
  }
}
// and with voiceTerminalId blank, to see whether that field is the constraint
for (const code of ['ZVB123','ZVB1234']) {
  const body = { ...base, deviceCode: code, deviceName: 'ZV probe', voiceTerminalId: '' };
  const r = await probe(page, { resource:'devices', caseName:`voice-create-noterm-len${code.length}`, method:'POST', urlPath:'/wm/devices', body,
    notes:'Same, but with voiceTerminalId blank.' });
  results.push(`${code} noTerm (len ${code.length}) -> ${r.response.status} ${r.response.kind}`);
  if (r.response.status === 201) {
    const id = r.response.body?.data?.resourceId;
    if (id) await probe(page, { resource:'devices', caseName:'voice-cleanup', method:'DELETE', urlPath:`/wm/devices/${encodeURIComponent(id)}` });
  }
}
console.log(results.join('\n'));
await browser.close();
