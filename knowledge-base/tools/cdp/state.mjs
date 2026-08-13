import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const ctx = b.contexts()[0];
for (const p of ctx.pages()) {
  console.log('URL:', p.url().slice(0, 130));
  console.log('TITLE:', await p.title().catch(() => '?'));
  const frames = p.frames().map(f => f.url().slice(0, 90)).filter(u => u && u !== 'about:blank');
  console.log('FRAMES:', frames.length, frames.slice(0, 4));
  console.log('TEXT:', (await p.locator('body').innerText().catch(() => '')).replace(/\s+/g, ' ').slice(0, 400));
}
// NOTE: do not close - browser.close() over CDP closes pages a concurrent run is using.
process.exit(0);
