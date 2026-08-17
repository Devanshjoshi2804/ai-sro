/* Recover a wedged screen: dismissing the modal is not enough, the masks survive it. */
import { chromium } from 'playwright';
import { dismissBlocking, goto } from './ext.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const before = await dismissBlocking(page);
// Masks outlive the modal on this screen, so force-remove them, then leave via the hash router.
const stripped = await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const masks = [...w.document.querySelectorAll('.x-mask')];
  masks.forEach(m => m.parentNode && m.parentNode.removeChild(m));
  return masks.length;
});
await goto(page, '#wm.config/wm.config.warehouse.warehouse////');
const after = await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  return { masks: w.document.querySelectorAll('.x-mask').length,
           visible: [...w.document.querySelectorAll('.x-mask')].filter(m=>m.getBoundingClientRect().width>0).length };
});
console.log(JSON.stringify({ dismissed: before.cleared.length, masksStripped: stripped, after }, null, 1));
await b.close();
