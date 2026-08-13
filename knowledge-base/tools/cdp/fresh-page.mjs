/* Recover from a crashed/overloaded page by opening a fresh tab in the SAME browser context,
 * which keeps the session cookies and avoids another manual login. */
import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const ctx = b.contexts()[0];
console.log('pages before:', ctx.pages().length);
const page = await ctx.newPage();
await page.goto('https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.partners.customers.types////', { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(9000);
console.log('new page title:', await page.title().catch(()=>'?'));
console.log('frames:', page.frames().length);
// close the crashed/older pages so the crawler picks the fresh one
for (const p of ctx.pages()) { if (p !== page) await p.close().catch(()=>{}); }
console.log('pages after cleanup:', ctx.pages().length);
await b.close();
